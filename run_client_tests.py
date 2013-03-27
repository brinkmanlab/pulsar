import shutil
import tempfile
import os
import optparse
import traceback

from lwr.lwr_client import Client
from lwr.lwr_client import FileStager

class MockTool(object):

    def __init__(self, tool_dir):
        self.id = "client_test"
        self.version = "1.0"
        self.tool_dir = tool_dir



def main():
    """ Exercises a running lwr server application with the lwr client. """
    parser = optparse.OptionParser()
    parser.add_option('--url', dest='url', default='http://localhost:8913/')
    parser.add_option('--private_token', default=None)
    (options, args) = parser.parse_args()

    try:
        temp_directory = tempfile.mkdtemp()
        temp_work_dir = os.path.join(temp_directory, "w")
        temp_tool_dir = os.path.join(temp_directory, "t")
        for dir in [temp_tool_dir, temp_work_dir]:
            os.makedirs(dir)

        temp_input_path = os.path.join(temp_directory, "input.txt")
        temp_config_path = os.path.join(temp_work_dir, "config.txt")
        temp_tool_path = os.path.join(temp_directory, "t", "script.py")
        temp_output_path = os.path.join(temp_directory, "output")

        temp_input_file = open(temp_input_path, "w")
        temp_config_file = open(temp_config_path, "w")
        temp_tool_file = open(temp_tool_path, "w")
        try:
            temp_input_file.write("Hello world input!!@!")
            temp_config_file.write("hello world output")
            temp_tool_file.write("""
import sys
output = open(sys.argv[3], 'w')
input_input = open(sys.argv[2], 'r')
config_input = open(sys.argv[1], 'r')
try:
    assert input_input.read() == "Hello world input!!@!"
    contents = config_input.read(1024)
    output.write(contents)
finally:
    output.close()
    config_input.close()
""")
        finally:
            temp_input_file.close()
            temp_tool_file.close()
            temp_config_file.close()

        command_line = "python %s '%s' '%s' '%s'" % (temp_tool_path, temp_config_path, temp_input_path, temp_output_path)
        config_files = [temp_config_path]
        input_files = [temp_input_path]
        output_files = [temp_output_path]

        client = Client({"url": options.url, "private_token": options.private_token}, "123456")
        stager = FileStager(client, MockTool(temp_tool_dir), command_line, config_files, input_files, output_files, temp_work_dir)
        new_command = stager.get_rewritten_command_line()
        client.launch(new_command)
        client.wait()
        client.download_output(temp_output_path, temp_directory)
        output_file = open(temp_output_path, 'r')
        try:
            output_contents = output_file.read()
            assert output_contents == "hello world output", "Invalid output_contents: %s" % output_contents
            print 'Test Successful!'
        finally:
            output_file.close()
    except BaseException, e:
        print "Exception: %s\n" % str(e)
        traceback.print_exc(e)
    finally:
        shutil.rmtree(temp_directory)
        # client.clean()

if __name__ == "__main__":
    main()
