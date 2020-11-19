
##############################################################################
# This code was copied+adapted from the Kubernetes examples, originally at
# this URL:
#
# https://github.com/kubernetes-client/python/blob/master/examples/pod_portforward.py
##############################################################################

# Copyright 2020 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Shows the functionality of portforward streaming using an nginx container.

"""

import select
import socket
import time

import six.moves.urllib.request as urllib_request

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import portforward

import urllib3.util.connection

##############################################################################
# Kubernetes pod port forwarding works by directly providing a socket which
# the python application uses to send and receive data on. This is in contrast
# to the go client, which opens a local port that the go application then has
# to open to get a socket to transmit data.
#
# This simplifies the python application, there is not a local port to worry
# about if that port number is available. Nor does the python application have
# to then deal with opening this local port. The socket used to transmit data
# is immediately provided to the python application.
#
# Below also is an example of monkey patching the socket.create_connection
# function so that DNS names of the following formats will access kubernetes
# ports:
#
#    <pod-name>.<namespace>.kubernetes
#    <pod-name>.pod.<namespace>.kubernetes
#    <service-name>.svc.<namespace>.kubernetes
#    <service-name>.service.<namespace>.kubernetes
#
# These DNS name can be used to interact with pod ports using python libraries,
# such as urllib.request and http.client. For example:
#
# response = urllib.request.urlopen(
#     'https://metrics-server.service.kube-system.kubernetes/'
# )
#
##############################################################################

class KubernetesPortforward(object):
    """Monkey-patches :py:class:`socket` with the ability to directly
    address Kubernetes pods + services.

    The idea is that for host names of the form
    ``[name].[pod|svc].[namespace].kubernetes`` we override the normal
    socket behaviour, and have it connect via port-forward to the
    appropriate pod instead.

    Yes, this is quite an... elaborate approach. Would be great if
    kubernetes-python would provide a better way.
    """

    def __init__(self, api_instance):
        self._api_instance = api_instance
        self._create_connection = socket.create_connection
        self._urllib3_create_connection = urllib3.util.connection.create_connection

    def _kubernetes_create_connection(self, address, *args, **kwargs):
        dns_name = address[0]
        if isinstance(dns_name, bytes):
            dns_name = dns_name.decode()
        dns_name = dns_name.split(".")
        if dns_name[-1] != 'kubernetes':
            return self._create_connection(address, *args, **kwargs)
        if len(dns_name) not in (3, 4):
            raise RuntimeError("Unexpected kubernetes DNS name.")
        namespace = dns_name[-2]
        name = dns_name[0]
        port = address[1]
        if len(dns_name) == 4:
            if dns_name[1] in ('svc', 'service'):
                service = self._api_instance.read_namespaced_service(name, namespace)
                for service_port in service.spec.ports:
                    if service_port.port == port:
                        port = service_port.target_port
                        break
                else:
                    raise RuntimeError(
                        "Unable to find service port: %s" % port)
                label_selector = []
                for key, value in service.spec.selector.items():
                    label_selector.append("%s=%s" % (key, value))
                pods = self._api_instance.list_namespaced_pod(
                    namespace, label_selector=",".join(label_selector)
                )
                if not pods.items:
                    raise RuntimeError("Unable to find service pods.")
                name = pods.items[0].metadata.name
                if isinstance(port, str):
                    for container in pods.items[0].spec.containers:
                        for container_port in container.ports:
                            if container_port.name == port:
                                port = container_port.container_port
                                break
                        else:
                            continue
                        break
                    else:
                        raise RuntimeError(
                            "Unable to find service port name: %s" % port)
            elif dns_name[1] != 'pod':
                raise RuntimeError(
                    "Unsupported resource type: %s" %
                    dns_name[1])
        print(f"K8s port-forward to {name}.{namespace}.kubernetes:{port}...")
        pf = portforward(self._api_instance.connect_get_namespaced_pod_portforward,
                         name, namespace, ports=str(port))
        return pf.socket(port)

    def __enter__(self):

        # Apply monkey-patches. We need to also overload urllib3 here,
        # because it similarly overrides the standard
        # create_connection with its own version.
        self._create_connection = socket.create_connection
        if hasattr(urllib3.util.connection, 'create_connection'):
            self._urllib3_create_connection = urllib3.util.connection.create_connection
        socket.create_connection = self._kubernetes_create_connection
        urllib3.util.connection.create_connection = self._kubernetes_create_connection
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Scope the client connection."""

        #socket.create_connection = self._create_connection
        #if hasattr(urllib3.util.connection, 'create_connection'):
        #    urllib3.util.connection.create_connection = self._urllib3_create_connection
        return False
