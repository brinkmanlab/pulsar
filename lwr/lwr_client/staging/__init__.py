from os.path import basename
from os.path import join
from os.path import dirname
from os import sep

from ..util import PathHelper

COMMAND_VERSION_FILENAME = "COMMAND_VERSION"


class ClientJobDescription(object):
    """ A description of how client views job - command_line, inputs, etc..

    **Parameters**

    command_line : str
        The local command line to execute, this will be rewritten for the remote server.
    config_files : list
        List of Galaxy 'configfile's produced for this job. These will be rewritten and sent to remote server.
    input_files :  list
        List of input files used by job. These will be transferred and references rewritten.
    output_files : list
        List of output_files produced by job.
    tool_dir : str
        Directory containing tool to execute (if a wrapper is used, it will be transferred to remote server).
    working_directory : str
        Local path created by Galaxy for running this job.
    requirements : list
        List of requirements for tool execution.
    version_file : str
        Path to version file expected on the client server
    arbitrary_files : dict()
        Additional non-input, non-tool, non-config, non-working directory files
        to transfer before staging job. This is most likely data indices but
        can be anything. For now these are copied into staging working
        directory but this will be reworked to find a better, more robust
        location.
    rewrite_paths : boolean
        Indicates whether paths should be rewritten in job inputs (command_line
        and config files) while staging files).
    """

    def __init__(
        self,
        tool,
        command_line,
        config_files,
        input_files,
        client_outputs,
        working_directory,
        requirements,
        arbitrary_files=None,
        rewrite_paths=True,
    ):
        self.tool = tool
        self.command_line = command_line
        self.config_files = config_files
        self.input_files = input_files
        self.client_outputs = client_outputs
        self.working_directory = working_directory
        self.requirements = requirements
        self.rewrite_paths = rewrite_paths
        self.arbitrary_files = arbitrary_files or {}

    @property
    def output_files(self):
        return self.client_outputs.output_files

    @property
    def version_file(self):
        return self.client_outputs.version_file


class ClientOutputs(object):
    """ Abstraction describing the output datasets EXPECTED by the Galaxy job
    runner client.
    """

    def __init__(self, working_directory, output_files, work_dir_outputs=None, version_file=None):
        self.working_directory = working_directory
        self.work_dir_outputs = work_dir_outputs
        self.output_files = output_files
        self.version_file = version_file

    def to_dict(self):
        return dict(
            working_directory=self.working_directory,
            work_dir_outputs=self.work_dir_outputs,
            output_files=self.output_files,
            version_file=self.version_file
        )

    @staticmethod
    def from_dict(config_dict):
        return ClientOutputs(
            working_directory=config_dict.get('working_directory'),
            work_dir_outputs=config_dict.get('work_dir_outputs'),
            output_files=config_dict.get('output_files'),
            version_file=config_dict.get('version_file'),
        )


class LwrOutputs(object):
    """ Abstraction describing the output files PRODUCED by the remote LWR
    server. """

    def __init__(self, working_directory_contents, output_directory_contents, remote_separator=sep):
        self.working_directory_contents = working_directory_contents
        self.output_directory_contents = output_directory_contents
        self.path_helper = PathHelper(remote_separator)

    @staticmethod
    def from_status_response(complete_response):
        # Default to None instead of [] to distinguish between empty contents and it not set
        # by the LWR - older LWR instances will not set these in complete response.
        working_directory_contents = complete_response.get("working_directory_contents", None)
        output_directory_contents = complete_response.get("outputs_directory_contents", None)
        # Older (pre-2014) LWR servers will not include separator in response,
        # so this should only be used when reasoning about outputs in
        # subdirectories (which was not previously supported prior to that).
        remote_separator = complete_response.get("system_properties", {}).get("separator", sep)
        return LwrOutputs(
            working_directory_contents,
            output_directory_contents,
            remote_separator
        )

    def has_output_file(self, output_file):
        if self.output_directory_contents is None:
            # Legacy LWR doesn't report this, return None indicating unsure if
            # output was generated.
            return None
        else:
            return basename(output_file) in self.output_directory_contents

    def has_output_directory_listing(self):
        return self.output_directory_contents is not None

    def output_extras(self, output_file):
        """
        Returns dict mapping local path to remote name.
        """
        if not self.has_output_directory_listing():
            # Fetching $output.extra_files_path is not supported with legacy
            # LWR (pre-2014) severs.
            return {}

        output_directory = dirname(output_file)

        def local_path(name):
            return join(output_directory, self.path_helper.local_name(name))

        files_directory = "%s_files%s" % (basename(output_file)[0:-len(".dat")], self.path_helper.separator)
        names = filter(lambda o: o.startswith(files_directory),  self.output_directory_contents)
        return dict(map(lambda name: (local_path(name), name), names))
