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
import pytest
from django.test.utils import override_settings

from paas_wl.platform.applications.models import BuildProcess, WlApp
from tests.paas_wl.utils.build import create_build_proc


@pytest.fixture(autouse=True, scope="session")
def no_color():
    with override_settings(COLORFUL_TERMINAL_OUTPUT=False):
        yield


@pytest.fixture
def wl_app(bk_stag_env, with_wl_apps) -> WlApp:
    """A WlApp object"""
    return bk_stag_env.wl_app


@pytest.fixture
def build_proc(wl_app) -> BuildProcess:
    """A new BuildProcess object with random info"""
    return create_build_proc(wl_app)
