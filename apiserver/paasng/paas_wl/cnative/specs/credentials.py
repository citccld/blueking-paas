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
from contextlib import contextmanager
from typing import Dict, Iterator, List

from paas_wl.cnative.specs.constants import IMAGE_CREDENTIALS_REF_ANNO_KEY
from paas_wl.platform.applications.models import WlApp
from paas_wl.resources.base import kres
from paas_wl.workloads.images.entities import ImageCredentialsManager as _ImageCredentialsManager
from paas_wl.workloads.images.models import AppUserCredential, ImageCredentialRef
from paasng.platform.applications.models import Application


def split_image(repository: str) -> str:
    return repository.rsplit(":", 1)[0]


def get_references(manifest: Dict) -> List[ImageCredentialRef]:
    """get image credentials references from manifest annotations

    :raise: ValueError if the value is an invalid json
    """
    annotations = manifest["metadata"]["annotations"]
    processes = manifest["spec"]["processes"]
    # dynamic build references from annotations
    refs = []
    for process in processes:
        proc_name = process["name"]
        anno_key = f"{IMAGE_CREDENTIALS_REF_ANNO_KEY}.{proc_name}"
        if anno_key not in annotations:
            continue
        refs.append(ImageCredentialRef(image=split_image(process["image"]), credential_name=annotations[anno_key]))
    return refs


def validate_references(application: Application, references: List[ImageCredentialRef]):
    """validate if the reference credentials is defined

    :raises: ValueError if the reference credentials is undefined
    TODO: 验证 credential 是否可以拉取对应的镜像
    """
    request_names = {ref.credential_name for ref in references}
    all_names = set(AppUserCredential.objects.list_all_name(application))
    if missing_names := request_names - all_names:
        raise ValueError(f"missing credentials {missing_names}")


class ImageCredentialsManager(_ImageCredentialsManager):
    """An ImageCredentialsManager using given k8s client, the client must be closed by outer logic"""

    def __init__(self, client):
        super().__init__()
        self._client = client

    def _kres(self, app: WlApp, api_version: str = '') -> Iterator[kres.BaseKresource]:
        """return kres object using given k8s client"""
        yield self.entity_type.Meta.kres_class(self._client, api_version=api_version)

    kres = contextmanager(_kres)
