# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import json
import subprocess

from osc_placement_tree.tests import base
from osc_placement_tree.tests import uuids


class TestBase(base.TestBase):
    VERSION = "1.14"

    @classmethod
    def openstack(cls, cmd, may_fail=False, use_json=False):
        result = None
        try:
            to_exec = ["openstack"] + cmd.split()
            if use_json:
                to_exec += ["-f", "json"]
            if cls.VERSION is not None:
                to_exec += ["--os-placement-api-version", cls.VERSION]

            output = subprocess.check_output(to_exec, stderr=subprocess.STDOUT)
            result = (output or b"").decode("utf-8")
        except subprocess.CalledProcessError as e:
            msg = 'Command: "%s"\noutput: %s' % (" ".join(e.cmd), e.output)
            e.cmd = msg
            if not may_fail:
                raise

        if use_json and result:
            return json.loads(result)
        else:
            return result

    def assertCommandFailed(self, message, func, *args, **kwargs):
        signature = [func]
        signature.extend(args)
        try:
            func(*args, **kwargs)
            self.fail("Command does not fail as required (%s)" % signature)

        except subprocess.CalledProcessError as e:
            self.assertIn(
                message,
                e.output,
                'Command "%s" fails with different message' % e.cmd,
            )

    def create_rp(self, rp_name, parent_rp_name=None):
        parent_rp_uuid = None
        if parent_rp_name:
            parent_rp_uuid = getattr(uuids, parent_rp_name)

        parent = (
            "--parent-provider %s" % parent_rp_uuid if parent_rp_uuid else ""
        )
        self.openstack(
            (
                "resource provider create %(name)s --uuid %(uuid)s "
                % {"name": rp_name, "uuid": getattr(uuids, rp_name)}
            )
            + parent
        )
        self.addCleanup(lambda: self.delete_rp(getattr(uuids, rp_name)))

    def delete_rp(self, rp_uuid):
        self.openstack("resource provider delete %s" % rp_uuid)

    def update_inventory(self, rp_name, *resources):
        cmd = "resource provider inventory set {uuid} {resources}".format(
            uuid=getattr(uuids, rp_name),
            resources=" ".join(["--resource %s" % r for r in resources]),
        )
        return self.openstack(cmd, use_json=True)

    def set_traits(self, rp_name, traits):
        traits_str = ""
        for trait in traits:
            traits_str += " --trait %s" % trait
        self.openstack(
            "resource provider trait set %s %s"
            % (getattr(uuids, rp_name), traits_str)
        )

    def set_aggregate(self, rp_name, aggregate_uuids):
        aggregate_str = ""
        for agg in aggregate_uuids:
            aggregate_str += " --aggregate %s" % agg
        self.openstack(
            "resource provider aggregate set %s %s"
            % (getattr(uuids, rp_name), aggregate_str)
        )

    def get_project_id(self, project_name):
        return self.openstack("project show %s" % project_name, use_json=True)[
            "id"
        ]

    def get_user_id(self, user_name):
        return self.openstack("user show %s" % user_name, use_json=True)["id"]

    def create_allocation(
        self, consumer_uuid, allocations, project_id, user_id
    ):
        allocs_str = " ".join(
            [
                "--allocation rp=%s,%s"
                % (
                    getattr(uuids, rp_name),
                    ",".join(
                        [
                            "%s=%s" % (rc, value)
                            for rc, value in resources.items()
                        ]
                    ),
                )
                for rp_name, resources in allocations.items()
            ]
        )
        cmd = (
            "--debug resource provider allocation set {consumer_uuid} "
            "--project-id {project_id} --user-id {user_id} "
            "{allocations}"
            "".format(
                consumer_uuid=consumer_uuid,
                project_id=project_id,
                user_id=user_id,
                allocations=allocs_str,
            )
        )

        self.openstack(cmd)
        self.addCleanup(lambda: self.delete_allocation(consumer_uuid))

    def delete_allocation(self, consumer_uuid):
        self.openstack(
            "resource provider allocation delete %s" % consumer_uuid
        )
