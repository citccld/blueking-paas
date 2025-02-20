import json
import logging
from typing import Dict, List, NamedTuple, Optional

from django.conf import settings

from paas_wl.cluster.shim import Cluster, RegionClusterService
from paas_wl.networking.entrance.addrs import URL, EnvExposedURL
from paasng.engine.configurations.provider import env_vars_providers
from paasng.engine.constants import AppEnvName
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.modules.constants import ExposedURLType
from paasng.platform.modules.helpers import get_module_clusters
from paasng.publish.entrance.domains import get_preallocated_domain, get_preallocated_domains_by_env
from paasng.publish.entrance.subpaths import get_preallocated_path, get_preallocated_paths_by_env
from paasng.publish.entrance.utils import get_legacy_url

logger = logging.getLogger(__name__)


def get_preallocated_url(module_env: ModuleEnvironment) -> Optional[EnvExposedURL]:
    """获取某环境的默认访问入口地址（不含独立域名)。

    - 地址为预计算生成，无需真实部署，不保证能访问
    """
    if items := get_preallocated_urls(module_env):
        return items[0]
    return None


def get_preallocated_urls(module_env: ModuleEnvironment) -> List[EnvExposedURL]:
    """获取某环境的所有可选访问入口地址（不含独立域名)。

    - 当集群配置了多个根域时，返回多个结果
    - 地址为预计算生成，无需真实部署，不保证能访问
    """
    module = module_env.module
    if module.exposed_url_type == ExposedURLType.SUBPATH:
        subpaths = get_preallocated_paths_by_env(module_env)
        return [EnvExposedURL(url=p.as_url(), provider_type='subpath') for p in subpaths]
    elif module.exposed_url_type == ExposedURLType.SUBDOMAIN:
        domains = get_preallocated_domains_by_env(module_env)
        return [EnvExposedURL(url=d.as_url(), provider_type='subdomain') for d in domains]
    elif module.exposed_url_type is None:
        if url := get_legacy_url(module_env):
            return [EnvExposedURL(url=URL.from_address(url), provider_type='legacy')]
    return []


@env_vars_providers.register_env
def _default_preallocated_urls(env: ModuleEnvironment) -> Dict[str, str]:
    """Append the default preallocated URLs, the value include both "stag" and "prod" environments
    for given module.
    """
    application = env.module.application
    clusters = get_module_clusters(env.module)
    addrs_value = ''
    try:
        addrs = get_preallocated_address(
            application.code, env.module.region, clusters=clusters, module_name=env.module.name
        )
        addrs_value = json.dumps(addrs._asdict())
    except ValueError:
        logger.warning('Fail to get preallocated address for application: %s, module: %s', application, env.module)
    return {settings.CONFIGVAR_SYSTEM_PREFIX + 'DEFAULT_PREALLOCATED_URLS': addrs_value}


class PreAddresses(NamedTuple):
    """Preallocated addresses, include both environments"""

    stag: str
    prod: str


def get_preallocated_address(
    app_code: str,
    region: Optional[str] = None,
    clusters: Optional[Dict[AppEnvName, Cluster]] = None,
    module_name: Optional[str] = None,
) -> PreAddresses:
    """Get the preallocated address for a application which was not released yet

    :param region: the region name on which the application will be deployed, if not given, use default region
    :param clusters: the env-cluster map, if not given, all use default cluster
    :param module_name: the module name, if not given, use default module
    :raises: ValueError no preallocated address can be found
    """
    region = region or settings.DEFAULT_REGION_NAME
    clusters = clusters or {}

    helper = RegionClusterService(region)
    stag_address, prod_address = "", ""

    # 生产环境
    prod_cluster = clusters.get(AppEnvName.PROD) or helper.get_default_cluster()
    prod_pre_subpaths = get_preallocated_path(app_code, prod_cluster.ingress_config, module_name=module_name)
    prod_pre_subdomains = get_preallocated_domain(app_code, prod_cluster.ingress_config, module_name=module_name)

    if prod_pre_subdomains:
        prod_address = prod_pre_subdomains.prod.as_url().as_address()

    # 若集群有子路径配置，则优先级高于子域名
    if prod_pre_subpaths:
        prod_address = prod_pre_subpaths.prod.as_url().as_address()

    # 测试环境
    stag_cluster = clusters.get(AppEnvName.STAG) or helper.get_default_cluster()
    stag_pre_subpaths = get_preallocated_path(app_code, stag_cluster.ingress_config, module_name=module_name)
    stag_pre_subdomains = get_preallocated_domain(app_code, stag_cluster.ingress_config, module_name=module_name)

    if stag_pre_subdomains:
        stag_address = stag_pre_subdomains.stag.as_url().as_address()

    # 若集群有子路径配置，则优先级高于子域名
    if stag_pre_subpaths:
        stag_address = stag_pre_subpaths.stag.as_url().as_address()

    if not (stag_address and prod_address):
        raise ValueError(
            "failed to get sub-path or sub-domain entrance config, "
            f"stag cluster: {stag_cluster.name}, prod cluster: {prod_cluster.name}"
        )

    return PreAddresses(stag=stag_address, prod=prod_address)


def get_bk_doc_url_prefix() -> str:
    """Obtain the address prefix of the BK Document Center,
    which is used for the product document address obtained by the app
    """
    if settings.BK_DOCS_URL_PREFIX:
        return settings.BK_DOCS_URL_PREFIX

    # Address for bk_docs_center saas
    # Remove the "/" at the end to ensure that the subdomain and subpath mode are handled in the same way
    return get_preallocated_address(settings.BK_DOC_APP_ID).prod.rstrip("/")


# pre-allocated addresses related functions end
