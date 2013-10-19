import os
import argparse
import script_helpers

parser = argparse.ArgumentParser()

source_root_help = ('All directories below this one that '
                    'contain images will be processed')
parser.add_argument('source_root',
                    help=source_root_help,
                    nargs=1)

group = parser.add_mutually_exclusive_group(required=True)
dest_root_help = ('If set, image directories below ``source-root`` '
                  'will be copied into this directory tree. Only directories '
                  'that contain image files will be copied; any '
                  'intermediary directories required to contain directories '
                  'that contain images will also be created.')
group.add_argument('--dest-root',
                   help=dest_root_help,
                   nargs=1)

group.add_argument('--overwrite-source',
                   help=('This flag must be used to overwrite images in '
                         'the course directory.'),
                   action='store_true'
                   )

parser.add_argument('--scripts-only',
                    help=('This script will write a single shell script '
                          'with the name provided in this option. No '
                          'images will be modified or directories created, '
                          'but the script can be run to do those things.'),
                    action='store_true')

object_list_help = ('Path to file containing list (and optionally '
                    'coordinates of) objects that might be in these files.'
                    ' If not provided it defaults to looking for a file '
                    'called obsinfo.txt in the directory being processed')
parser.add_argument('-o', '--object-list',
                    help=object_list_help,
                    default=None)

parser.add_argument('--quiet-log',
                    help=('Log only warnings (or worse) to '
                          'FILES AND CONSOLE while running scripts'),
                    action='store_true')

script_helpers.add_console_output_args(parser)
script_helpers.add_debug(parser)

args = parser.parse_args()

common_args = []

verbose = '-v' if not args.quiet_log else ''
quiet_console = '--quiet-console' if args.quiet_console else ''
silent_console = '--silent-console' if args.silent_console else ''
common_args.extend([verbose, quiet_console, silent_console])

object_list_option = []
if args.object_list is not None:
    object_list_option = ['--object-list', args.object_list]

source_root = args.source_root[0]

import subprocess


def construct_command(script_name, source, destination,
                      common_arguments, additional_args=None):
    command = ['python', script_name]
    command.extend(common_arguments)
    command.extend(['--destination-dir', destination])
    if additional_args:
        command.extend(additional_args)
    command.extend([source])
    command = [arg for arg in command if arg]
    return command

from image_collection import ImageFileCollection

dest_root = args.dest_root or [source_root]
dest_root = dest_root[0]

# check that source and destination roots are not same unless user has
# explicitly requested overwrite
if (dest_root == source_root) & (not args.overwrite_source):
    raise RuntimeError('Will not overwrite source unless you explicitly use '
                       'the option --overwrite-source')

sep_repeat = 20
separator_format = '#' * sep_repeat + ' {} ' + '#' * sep_repeat

all_commands = []
script_name = 'header_process_script.sh'

for root, dirs, files in os.walk(source_root):
    if not files:
        continue

    # I should probably make sure there are fits files in here.
    # Not going to...

    # Oh fine, I will test.
    fits_collection = ImageFileCollection(root)
    if not fits_collection.files:
        continue

    source_rel_to_root = os.path.relpath(root, source_root)
    destination = os.path.join(dest_root, source_rel_to_root)

    # Construct strings that will be used to actually do the processing
    make_destination = ['mkdir', '-p', destination]
    run_patch = construct_command('run_patch.py', root, destination,
                                  common_args,
                                  additional_args=object_list_option)
    # NOTE: after header patching all other scripts should use as their
    # input the directory that was the destination for run_patch
    run_astrometry = construct_command('run_astrometry.py', destination,
                                       destination, common_args)
    run_triage = construct_command('run_triage.py', destination, destination,
                                   common_args)

    cmd_list = [separator_format.format('START commands for {}'.format(root))]
    for cmd in [make_destination, run_patch, run_astrometry, run_triage]:
        cmd_list.append(' '.join(cmd))
    end_str = separator_format.format('END commands for {}'.format(root))
    cmd_list.append(end_str)
    cmd_list = '\n'.join(cmd_list) + '\n'*5
    with open(script_name, mode='a') as f:
        f.write(cmd_list)

    if not args.scripts_only:
        subprocess.call(make_destination)
        script_path = os.path.join(destination, script_name)
        with open(script_path, 'wb') as script_to_reproduce_this:
            script_to_reproduce_this.write(cmd_list)
        subprocess.call(run_patch)
        subprocess.call(run_astrometry)
        subprocess.call(run_triage)