/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package reconcilers

import (
	"context"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	"k8s.io/apimachinery/pkg/util/intstr"
	"sigs.k8s.io/controller-runtime/pkg/client/fake"

	paasv1alpha2 "bk.tencent.com/paas-app-operator/api/v1alpha2"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/labels"
	"bk.tencent.com/paas-app-operator/pkg/controllers/resources/names"
)

var _ = Describe("Test ServiceReconciler", func() {
	var bkapp *paasv1alpha2.BkApp
	var builder *fake.ClientBuilder
	var scheme *runtime.Scheme
	var fakeService *corev1.Service
	ctx := context.Background()

	BeforeEach(func() {
		bkapp = &paasv1alpha2.BkApp{
			TypeMeta: metav1.TypeMeta{
				Kind:       paasv1alpha2.KindBkApp,
				APIVersion: paasv1alpha2.GroupVersion.String(),
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:      "bkapp-sample",
				Namespace: "default",
			},
			Spec: paasv1alpha2.AppSpec{
				Build: paasv1alpha2.BuildConfig{
					Image: "nginx:latest",
				},
				Processes: []paasv1alpha2.Process{
					{
						Name:         "web",
						Replicas:     paasv1alpha2.ReplicasTwo,
						ResQuotaPlan: paasv1alpha2.ResQuotaPlanDefault,
						TargetPort:   80,
					},
				},
			},
		}

		fakeService = &corev1.Service{
			TypeMeta: metav1.TypeMeta{
				APIVersion: "v1",
				Kind:       "Service",
			},
			ObjectMeta: metav1.ObjectMeta{
				Name:        names.Deployment(bkapp, "fake"),
				Namespace:   bkapp.Namespace,
				Labels:      labels.Deployment(bkapp, "fake"),
				Annotations: make(map[string]string),
			},
			Spec: corev1.ServiceSpec{
				Ports: []corev1.ServicePort{
					{
						Name:       "http",
						Port:       80,
						TargetPort: intstr.FromInt(80),
						Protocol:   corev1.ProtocolTCP,
					},
				},
				Selector: labels.Deployment(bkapp, "fake"),
			},
		}

		builder = fake.NewClientBuilder()
		scheme = runtime.NewScheme()
		Expect(paasv1alpha2.AddToScheme(scheme)).NotTo(HaveOccurred())
		Expect(corev1.AddToScheme(scheme)).NotTo(HaveOccurred())
		builder.WithScheme(scheme)
	})

	It("test Reconcile", func() {
		outdated := fakeService.DeepCopy()
		web := fakeService.DeepCopy()
		web.Name = names.Service(bkapp, "web")
		r := NewServiceReconciler(builder.WithObjects(outdated).Build())

		result := r.Reconcile(context.Background(), bkapp)
		Expect(result.ShouldAbort()).To(BeFalse())

		got := corev1.ServiceList{}
		_ = r.Client.List(ctx, &got)
		Expect(len(got.Items)).To(Equal(1))
		Expect(got.Items[0].Name).To(Equal(names.Service(bkapp, "web")))
	})

	Context("test get current state", func() {
		It("not any Service exists", func() {
			r := NewServiceReconciler(builder.Build())
			svcList, err := r.listCurrentServices(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(svcList)).To(Equal(0))
		})

		It("with a Service", func() {
			client := builder.WithObjects(fakeService).Build()
			r := NewServiceReconciler(client)
			svcList, err := r.listCurrentServices(context.Background(), bkapp)
			Expect(err).NotTo(HaveOccurred())
			Expect(len(svcList)).To(Equal(1))
		})
	})

	It("test getWantedService", func() {
		r := NewServiceReconciler(builder.Build())
		svcList := r.getWantedService(bkapp)

		Expect(len(svcList)).To(Equal(1))
		Expect(svcList[0].Name).To(Equal(names.Service(bkapp, "web")))
	})

	It("test handleUpdate", func() {
		current := fakeService.DeepCopy()
		want := fakeService.DeepCopy()
		cli := builder.WithObjects(current).Build()
		r := NewServiceReconciler(cli)

		Expect(r.handleUpdate(ctx, cli, current, want)).NotTo(HaveOccurred())

		serviceLookupKey := types.NamespacedName{Namespace: current.GetNamespace(), Name: current.GetName()}
		got1 := corev1.Service{}
		_ = cli.Get(ctx, serviceLookupKey, &got1)

		Expect(got1.Spec.Selector).To(Equal(current.Spec.Selector))
		Expect(got1.Spec.Ports).To(Equal(current.Spec.Ports))

		By("change Service.Spec")
		want.Spec.Selector[paasv1alpha2.ProcessNameKey] = "web"

		Expect(want.Spec.Selector).NotTo(Equal(current.Spec.Selector))
		Expect(r.handleUpdate(ctx, cli, current, want)).NotTo(HaveOccurred())

		got2 := corev1.Service{}
		_ = cli.Get(ctx, serviceLookupKey, &got2)

		Expect(got2.Spec.Selector).NotTo(Equal(got1.Spec.Selector))
		Expect(got2.Spec.Selector).To(Equal(want.Spec.Selector))
	})
})
