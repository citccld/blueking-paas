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
"""Resource Definition of `BkApplication` kind.

Use `pydantic` to get good JSON-Schema support, which is essential for CRD.
"""
import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator

from paas_wl.cnative.specs.apis import ObjectMetadata
from paas_wl.cnative.specs.constants import ApiVersion, MResPhaseType, ResQuotaPlan
from paas_wl.release_controller.constants import ImagePullPolicy

# Default resource limitations for each process
DEFAULT_PROC_CPU = '500m'
DEFAULT_PROC_MEM = '256Mi'


class MetaV1Condition(BaseModel):
    """Condition contains details for one aspect of the current state of this API Resource"""

    type: str
    status: Literal["True", "False", "Unknown"] = "Unknown"
    reason: str
    message: str
    observedGeneration: int = Field(default=0)


class AutoscalingSpec(BaseModel):
    """Autoscaling specification"""

    enabled: bool
    minReplicas: int
    maxReplicas: int
    policy: str = Field(..., min_length=1)


class BkAppProcess(BaseModel):
    """Process resource"""

    name: str
    replicas: int = 1
    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)
    targetPort: Optional[int] = None
    resQuotaPlan: Optional[ResQuotaPlan] = None
    autoscaling: Optional[AutoscalingSpec] = None

    # Deprecated: use resQuotaPlan instead in v1alpha2
    cpu: str = DEFAULT_PROC_CPU
    # Deprecated: use resQuotaPlan instead in v1alpha2
    memory: str = DEFAULT_PROC_MEM
    # Deprecated: use spec.build.image instead in v1alpha2
    image: Optional[str] = None
    # Deprecated: use spec.build.imagePullPolicy instead in v1alpha2
    imagePullPolicy: str = ImagePullPolicy.IF_NOT_PRESENT


class Hook(BaseModel):
    """A hook object"""

    command: Optional[List[str]] = Field(default_factory=list)
    args: Optional[List[str]] = Field(default_factory=list)


class BkAppHooks(BaseModel):
    """Hook commands for BkApp"""

    preRelease: Optional[Hook] = None


class EnvVar(BaseModel):
    """Environment variable key-value pair"""

    name: str
    value: str


class BkAppConfiguration(BaseModel):
    """Configuration for BkApp"""

    env: List[EnvVar] = Field(default_factory=list)


class ReplicasOverlay(BaseModel):
    """Overwrite process's replicas by environment"""

    envName: str
    process: str
    count: int


class EnvVarOverlay(BaseModel):
    """Overwrite or add application's environment vars by environment"""

    envName: str
    name: str
    value: str


class AutoscalingOverlay(BaseModel):
    """Overwrite or add application's autoscaling by environment"""

    envName: str
    process: str
    policy: str


class EnvOverlay(BaseModel):
    """Defines environment specified configs"""

    replicas: Optional[List[ReplicasOverlay]] = None
    envVariables: Optional[List[EnvVarOverlay]] = None
    autoscaling: Optional[List[AutoscalingOverlay]] = None


class BkAppBuildConfig(BaseModel):
    """BuildConfig for BkApp"""

    # 兼容使用注解支持多镜像的场景（v1alpha1 遗留功能）
    image: Optional[str] = None
    imagePullPolicy: str = ImagePullPolicy.IF_NOT_PRESENT
    imageCredentialsName: Optional[str] = None
    dockerfile: Optional[str] = None
    buildTarget: Optional[str] = None
    args: Optional[Dict[str, str]] = None


class BkAppAddonSpec(BaseModel):
    """AddonSpec for BkApp"""

    name: str
    value: str


class BkAppAddon(BaseModel):
    """Addon for BkApp"""

    name: str
    specs: List[BkAppAddonSpec] = Field(default_factory=list)


class BkAppSpec(BaseModel):
    """Spec of BkApp resource"""

    build: Optional[BkAppBuildConfig] = None
    processes: List[BkAppProcess] = Field(default_factory=list)
    hooks: Optional[BkAppHooks] = None
    addons: List[BkAppAddon] = Field(default_factory=list)
    configuration: BkAppConfiguration = Field(default_factory=BkAppConfiguration)
    envOverlay: Optional[EnvOverlay] = None


class BkAppStatus(BaseModel):
    """BkAppStatus defines the observed state of BkApp"""

    phase: str = MResPhaseType.AppPending
    observedGeneration: int = Field(default=0)
    conditions: List[MetaV1Condition] = Field(default_factory=list)
    lastUpdate: Optional[datetime.datetime]


class BkAppResource(BaseModel):
    """Blueking Application resource"""

    apiVersion: str = ApiVersion.V1ALPHA2.value
    kind: Literal['BkApp'] = 'BkApp'
    metadata: ObjectMetadata
    spec: BkAppSpec
    status: BkAppStatus = Field(default_factory=BkAppStatus)

    @validator('apiVersion')
    def validate_api_version(cls, v) -> str:
        """ApiVersion can not be used for "Literal" validation directly, so we define a
        custom validator instead.
        """
        if v not in [ApiVersion.V1ALPHA2, ApiVersion.V1ALPHA1]:
            raise ValueError(f'{v} is not valid, use {ApiVersion.V1ALPHA2} or {ApiVersion.V1ALPHA1}')
        return v

    def to_deployable(self) -> Dict:
        """Return the deployable manifest, some fields are excluded."""
        # Set `exclude_none` to remove all fields whose value is `None` because
        # entries such as `"hooks": null` is not processable in Kubernetes 1.18.
        return self.dict(exclude_none=True, exclude={"status"})
