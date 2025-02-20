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
import logging
import re
from typing import TYPE_CHECKING, Dict

from paasng.engine.exceptions import DuplicateNameInSamePhaseError, StepNotInPresetListError
from paasng.engine.models.steps import StepMetaSet
from paasng.engine.utils.output import RedisChannelStream
from paasng.platform.modules.helpers import ModuleRuntimeManager

if TYPE_CHECKING:
    from paasng.engine.models import EngineApp
    from paasng.engine.models.phases import DeployPhase


logger = logging.getLogger()


class DeployStepPicker:
    """部署步骤选择器"""

    @classmethod
    def pick(cls, engine_app: 'EngineApp') -> StepMetaSet:
        """通过 engine_app 选择部署阶段应该绑定的步骤"""
        m = ModuleRuntimeManager(engine_app.env.module)
        # 以 SlugBuilder 匹配为主, 不存在绑定直接走缺省步骤集
        builder = m.get_slug_builder(raise_exception=False)
        if builder is None:
            return cls._get_default_meta_set()

        meta_sets = StepMetaSet.objects.filter(metas__builder_provider=builder).order_by("-created").distinct()
        if not meta_sets:
            return cls._get_default_meta_set()

        # NOTE: 目前一个 builder 只会关联一个 StepMetaSet
        return meta_sets[0]

    @classmethod
    def _get_default_meta_set(self):
        """防止由于后台配置缺失而影响部署流程, 绑定默认的 StepMetaSet"""
        try:
            best_matched_set = StepMetaSet.objects.get(is_default=True)
        except StepMetaSet.DoesNotExist:
            best_matched_set = StepMetaSet.objects.all().latest('-created')
        except StepMetaSet.MultipleObjectsReturned:
            best_matched_set = StepMetaSet.objects.filter(is_default=True).order_by("-created")[0]
        return best_matched_set


def update_step_by_line(line: str, pattern_maps: Dict, phase: 'DeployPhase'):
    """Try to find a match for the given log line in the given pattern maps. If a
    match is found, update the step status and write to stream.

    :param line: The log line to match.
    :param patterns_maps: The pattern maps to match against.
    :param phase: The deployment phase.
    """
    for job_status, pattern_map in pattern_maps.items():
        for pattern, step_name in pattern_map.items():
            match = re.compile(pattern).findall(line)
            # 未能匹配上任何预设匹配集
            if not match:
                continue

            try:
                step_obj = phase.get_step_by_name(step_name)
            except (StepNotInPresetListError, DuplicateNameInSamePhaseError):
                logger.debug("Step not found or duplicated, name: %s", step_name)
                continue

            # 由于日志会被重复处理，所以肯定会重复判断，当状态一致或处于已结束状态时，跳过
            if step_obj.status == job_status.value or step_obj.is_completed:
                continue

            logger.info("[%s] going to mark & write to stream", phase.deployment.id)
            # 更新 step 状态，并写到输出流
            step_obj.mark_and_write_to_stream(RedisChannelStream.from_deployment_id(phase.deployment.id), job_status)
