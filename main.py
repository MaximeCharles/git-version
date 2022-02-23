import argparse
import os
from git import Repo
from config import Config
from git_version import GitVersion


def start(parameters):
    config = Config(os.path.join(parameters.path, parameters.config))
    repo = Repo(parameters.path)
    if 'environment' in parameters and parameters.environment is not None:
        r = next((f for f in config.definitions if f.name == parameters.environment), None)
        if r is None:
            print(f'The environment {parameters.environment} is not found in the config')
        else:
            git_version = GitVersion(repo, r, parameters.push)
            version = git_version.get_new_version(parameters.build_number)
            git_version.tag_current_commit(version)
            print(version)
    else:
        for definition in config.definitions:
            git_version = GitVersion(repo, definition, parameters.push)
            version = git_version.get_new_version(parameters.build_number)
            git_version.tag_current_commit(version)
            print(f"{definition.name}: {version}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Setup version based on git')
    parser.add_argument('--environment', help='The name of the environment to compute', type=str, default=None)
    parser.add_argument('--path', help='The path of the .git folder', type=str, default='.')
    parser.add_argument('--config', help='The path of the config file', type=str, default='version.yml')
    parser.add_argument('--build-number', help='The build number wanted', type=int, default=None)
    parser.add_argument('--no-push', help='Auto push changes', dest='push',
                        action='store_false')
    parser.set_defaults(func=start)

    args = parser.parse_args()
    args.func(args)
