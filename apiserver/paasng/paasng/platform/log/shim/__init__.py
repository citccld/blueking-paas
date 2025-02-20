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

from django.conf import settings

from paas_wl.cluster.constants import ClusterFeatureFlag
from paas_wl.cluster.shim import EnvClusterService
from paasng.platform.applications.models import ModuleEnvironment
from paasng.platform.log.constants import LogCollectorType
from paasng.platform.log.shim.setup_bklog import setup_default_bk_log_model
from paasng.platform.log.shim.setup_elk import setup_saas_elk_model


def setup_env_log_model(env: ModuleEnvironment):
    cluster = EnvClusterService(env).get_cluster()
    if cluster.has_feature_flag(ClusterFeatureFlag.ENABLE_BK_LOG_COLLECTOR):
        return setup_default_bk_log_model(env)
    if settings.LOG_COLLECTOR_TYPE != LogCollectorType.ELK:
        raise ValueError("ELK is not supported")
    return setup_saas_elk_model(env)
