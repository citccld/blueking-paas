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
import uuid
from unittest import mock

import pytest
from blue_krill.async_utils.poll_task import CallbackResult, CallbackStatus

from paasng.dev_resources.sourcectl.exceptions import GetAppYamlError, GetProcfileError
from paasng.engine.constants import JobStatus
from paasng.engine.deploy.building import ApplicationBuilder, BuildProcessResultHandler
from paasng.engine.handlers import attach_all_phases
from paasng.engine.models import Deployment, DeployPhaseTypes
from paasng.engine.models.managers import DeployPhaseManager
from tests.utils.mocks.engine import mock_cluster_service
from tests.utils.mocks.poll_task import FakeTaskPoller

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_cluster():
    with mock_cluster_service():
        yield


class TestApplicationBuilder:
    """Tests for ApplicationBuilder"""

    @pytest.fixture
    def mock_get_app_yaml(self):
        with mock.patch(
            'paasng.engine.configurations.source_file.MetaDataFileReader.get_app_desc'
        ) as mocked_get_app_yaml:
            mocked_get_app_yaml.side_effect = GetAppYamlError('')
            yield

    def test_failed_when_parsing_processes(self, init_tmpls, bk_deployment_full, mock_get_app_yaml):
        with mock.patch(
            'paasng.engine.configurations.source_file.MetaDataFileReader.get_procfile'
        ) as mocked_get_procfile, mock.patch('paasng.engine.utils.output.RedisChannelStream') as mocked_stream:
            mocked_get_procfile.side_effect = GetProcfileError('Invalid Procfile format')
            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = ApplicationBuilder.from_deployment_id(bk_deployment_full.id)
            builder.start()

            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.FAILED.value
            assert deployment.err_detail == 'Procfile error: Invalid Procfile format'

            assert mocked_stream().write_title.called
            assert mocked_stream().write_title.call_args[0][0] == '正在解析应用进程信息'
            assert mocked_stream().write_message.called
            assert (
                mocked_stream().write_message.call_args[0][0]
                == '步骤 [解析应用进程信息] 出错了，原因：Procfile error: Invalid Procfile format。'
            )

    def test_failed_when_upload_source(self, init_tmpls, bk_deployment_full, mock_get_app_yaml):
        with mock.patch(
            'paasng.engine.configurations.source_file.MetaDataFileReader.get_procfile'
        ) as mocked_get_procfile, mock.patch(
            'paasng.engine.deploy.building.ApplicationBuilder.compress_and_upload'
        ) as mocked_c_and_upload, mock.patch(
            'paasng.engine.utils.output.RedisChannelStream'
        ) as mocked_stream:
            mocked_get_procfile.return_value = {"web": "gunicorn"}
            mocked_c_and_upload.side_effect = RuntimeError("Unable to upload")

            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = ApplicationBuilder.from_deployment_id(bk_deployment_full.id)
            builder.start()

            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.FAILED.value
            assert deployment.err_detail == 'Unable to upload'

            assert mocked_stream().write_title.called
            assert mocked_stream().write_title.call_args[0][0] == '正在上传仓库代码'
            assert mocked_stream().write_message.called
            assert mocked_stream().write_message.call_args[0][0] == '步骤 [上传仓库代码] 出错了，请稍候重试。'

    def test_start_normal(self, init_tmpls, bk_deployment_full, mock_get_app_yaml):
        with mock.patch(
            'paasng.engine.configurations.source_file.MetaDataFileReader.get_procfile'
        ) as mocked_get_procfile, mock.patch(
            'paasng.engine.deploy.building.ApplicationBuilder.compress_and_upload'
        ), mock.patch(
            'paasng.engine.deploy.building.BuildProcessPoller'
        ) as mocked_poller, mock.patch(
            'paasng.engine.utils.output.RedisChannelStream'
        ) as mocked_stream, mock.patch(
            'paasng.engine.deploy.building.start_buildpacks_build'
        ) as mocker_start_buildpacks_build:
            mocked_get_procfile.return_value = {"web": "gunicorn"}
            # Return a fake build_process ID
            faked_build_process_id = uuid.uuid4().hex
            mocker_start_buildpacks_build.return_value = faked_build_process_id

            attach_all_phases(sender=bk_deployment_full.app_environment, deployment=bk_deployment_full)
            builder = ApplicationBuilder.from_deployment_id(bk_deployment_full.id)
            builder.start()

            # Validate deployment data
            deployment = Deployment.objects.get(pk=bk_deployment_full.id)
            assert deployment.status == JobStatus.PENDING.value
            assert deployment.build_process_id.hex == faked_build_process_id
            assert deployment.err_detail is None

            # Validate "start_build_process" arguments
            assert mocker_start_buildpacks_build.called
            (
                _,
                version,
                stream_channel_id,
                source_tar_path,
                procfile,
                env_vars,
            ) = mocker_start_buildpacks_build.call_args[0]
            assert version.revision == deployment.source_revision
            assert stream_channel_id == str(bk_deployment_full.id)
            assert source_tar_path != ''
            assert procfile == {'web': 'gunicorn'}

            # Validate other arguments
            assert mocked_stream().write_title.called
            assert mocked_poller.start.called
            assert mocked_poller.start.call_args[0][0] == {
                "build_process_id": deployment.build_process_id.hex,
                "deployment_id": deployment.id,
            }


class TestBuildProcessResultHandler:
    """Tests for BuildProcessResultHandler"""

    @pytest.fixture(autouse=True)
    def auto_binding_phases(self, bk_prod_env, deployment):
        manager = DeployPhaseManager(bk_prod_env)
        phases = manager.get_or_create_all()
        for p in phases:
            manager.attach(DeployPhaseTypes(p.type), deployment)

    @pytest.fixture
    def deployment(self, bk_module, bk_deployment):
        bk_deployment.build_process_id = uuid.uuid4().hex
        return bk_deployment

    @pytest.mark.parametrize(
        'result,status',
        [
            (CallbackResult(status=CallbackStatus.EXCEPTION), JobStatus.FAILED.value),
            (CallbackResult(status=CallbackStatus.NORMAL), JobStatus.FAILED.value),
        ],
    )
    def test_failed(self, result, status, bk_module, deployment):
        params = {'build_process_id': deployment.build_process_id, 'deployment_id': deployment.id}
        BuildProcessResultHandler().handle(result, FakeTaskPoller.create(params))

        deployment.refresh_from_db()
        assert deployment.status == status

    def test_succeeded(self, bk_module, deployment):
        params = {'build_process_id': deployment.build_process_id, 'deployment_id': deployment.id}
        result = CallbackResult(
            status=CallbackStatus.NORMAL,
            data={'build_id': deployment.id.hex, 'build_status': JobStatus.SUCCESSFUL.value},
        )

        with mock.patch('paasng.engine.deploy.building.start_release_step') as mocked_release_mgr:
            BuildProcessResultHandler().handle(result, FakeTaskPoller.create(params))
            deployment.refresh_from_db()
            assert deployment.status == JobStatus.PENDING.value
            assert mocked_release_mgr.called
