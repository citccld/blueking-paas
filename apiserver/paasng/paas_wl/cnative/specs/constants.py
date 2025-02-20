# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

# Default resource limitations for each process
DEFAULT_PROC_CPU = '500m'
DEFAULT_PROC_MEM = '256Mi'

DEFAULT_PROCESS_NAME = 'web'

# 注解中存储当前应用是否启用白名单功能的键名
ACCESS_CONTROL_ANNO_KEY = "bkapp.paas.bk.tencent.com/access-control"
# workloads 注入到 annotations 的部署ID字段
BKPAAS_DEPLOY_ID_ANNO_KEY = "bkapp.paas.bk.tencent.com/bkpaas-deploy-id"
# workloads 注入到 annotations 的增强服务信息字段
BKPAAS_ADDONS_ANNO_KEY = "bkapp.paas.bk.tencent.com/addons"
# 注解中存储 region 的键名
BKAPP_REGION_ANNO_KEY = "bkapp.paas.bk.tencent.com/region"
# 注解或标签中存储应用名称的键名
BKAPP_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/name"
# 注解中存储应用 ID 的键名
BKAPP_CODE_ANNO_KEY = "bkapp.paas.bk.tencent.com/code"
# 注解中存储模块名称的键名
MODULE_NAME_ANNO_KEY = "bkapp.paas.bk.tencent.com/module-name"
# 注解中存储当前部署环境的键名
ENVIRONMENT_ANNO_KEY = "bkapp.paas.bk.tencent.com/environment"
# 注解中存储镜像凭证引用的键名
IMAGE_CREDENTIALS_REF_ANNO_KEY = "bkapp.paas.bk.tencent.com/image-credentials"
# 注解中存储数据统计站点ID的键名
PA_SITE_ID_ANNO_KEY = "bkapp.paas.bk.tencent.com/paas-analysis-site-id"
# LegacyProcImageAnnoKey, In API version "v1alpha1", every process can use a different image.
# This behaviour was changed in "v1alpha2", but we still need to save the legacy images configs
# in annotations to maintain backward compatibility.
LEGACY_PROC_IMAGE_ANNO_KEY = "bkapp.paas.bk.tencent.com/legacy-proc-image-config"
# LegacyProcResAnnoKey, In API version "v1alpha1", every process can specify the exact CPU and
# memory resources. This behaviour was changed in "v1alpha2", but we still need to save the
# legacy resource configs in annotations to maintain backward compatibility.
LEGACY_PROC_RES_ANNO_KEY = "bkapp.paas.bk.tencent.com/legacy-proc-res-config"


# 轮询云原生应用的部署状态时，如果获取到失败状态的次数超过最大容忍次数，就认为部署失败
CNATIVE_DEPLOY_STATUS_POLLING_FAILURE_LIMITS = 3


class ApiVersion(str, StructuredEnum):
    """Kubernetes CRD API versions"""

    V1ALPHA1 = 'paas.bk.tencent.com/v1alpha1'
    V1ALPHA2 = 'paas.bk.tencent.com/v1alpha2'


class DeployStatus(str, StructuredEnum):
    """Cloud-native app's deployment statuses"""

    PENDING = EnumField('pending', label=_('待实施'))
    PROGRESSING = EnumField('progressing', label=_('进行中'))
    READY = EnumField('ready', label=_('已就绪'))
    ERROR = EnumField('error', label=_('错误'))
    UNKNOWN = EnumField('unknown', label=_('未知'))

    @classmethod
    def is_stable(cls, val: 'DeployStatus') -> bool:
        """Check if a status is stable, which means it will not transform into
        other statuses.
        """
        return val in [DeployStatus.READY, DeployStatus.ERROR]


class DomainGroupSource(str, StructuredEnum):
    """The source types for DomainGroup data"""

    SUBDOMAIN = 'subdomain'
    SUBPATH = 'subpath'
    CUSTOM = 'custom'


class MResConditionType(str, StructuredEnum):
    APP_AVAILABLE = EnumField("AppAvailable")
    APP_PROGRESSING = EnumField("AppProgressing")
    ADDONS_PROVISIONED = EnumField("AddOnsProvisioned")
    HOOKS_FINISHED = EnumField("HooksFinished")


class ConditionStatus(str, StructuredEnum):
    """k8s metav1.ConditionStatus"""

    TRUE = EnumField("True")
    FALSE = EnumField("False")
    UNKNOWN = EnumField("Unknown")


class MResPhaseType(str, StructuredEnum):
    """a label for the condition of a BkApp at the current time."""

    AppPending = EnumField("Pending")
    AppRunning = EnumField("Running")
    AppFailed = EnumField("Failed")


class ScalingPolicy(str, StructuredEnum):
    """ScalingPolicy is used to specify which policy should be used while scaling"""

    # the default autoscaling policy (cpu utilization 85%)
    DEFAULT = EnumField("default")


class ResQuotaPlan(str, StructuredEnum):
    """ResQuotaPlan is used to specify process resource quota"""

    P_DEFAULT = EnumField("default")
    P_1C512M = EnumField("1C512M")
    P_2C1G = EnumField("2C1G")
    P_2C2G = EnumField("2C2G")
    P_4C1G = EnumField("4C1G")
    P_4C2G = EnumField("4C2G")
    P_4C4G = EnumField("4C4G")


# 资源配额方案到配额的映射表
PLAN_TO_QUOTA_PLAN = {
    ResQuotaPlan.P_DEFAULT: (DEFAULT_PROC_CPU, DEFAULT_PROC_MEM),
    ResQuotaPlan.P_1C512M: ("1000m", "512Mi"),
    ResQuotaPlan.P_2C1G: ("2000m", "1024Mi"),
    ResQuotaPlan.P_2C2G: ("2000m", "2048Mi"),
    ResQuotaPlan.P_4C1G: ("4000m", "1024Mi"),
    ResQuotaPlan.P_4C2G: ("4000m", "2048Mi"),
    ResQuotaPlan.P_4C4G: ("4000m", "4096Mi"),
}
