from enum import Enum
from typing import Optional, List
import yaml
import semver
from abc import ABC, abstractmethod


class BaseBranchFilter(ABC):
    @abstractmethod
    def is_match(self, branch_name) -> bool:
        pass


class OnlyBranchFilter(BaseBranchFilter):
    branches: List[str]

    def __init__(self, c):
        self.branches = c

    def is_match(self, branch_name: str) -> bool:
        if branch_name in self.branches:
            return True
        return False


class IgnoreBranchFilter(BaseBranchFilter):
    branches: List[str]

    def __init__(self, c):
        self.branches = c

    def is_match(self, branch_name) -> bool:
        if branch_name in self.branches:
            return False
        return True


class NoFilterBranch(BaseBranchFilter):
    def is_match(self, branch_name):
        return False


class BumpType(Enum):
    Major = 0
    Minor = 1
    Patch = 2
    Build = 3


class EnvironmentDefinition:
    is_prerelease: bool = False
    prerelease_tag: Optional[str] = None
    auto_tag: bool = False
    name = 'main'
    branch_filter = NoFilterBranch()
    bump_type: BumpType = BumpType.Patch

    def __init__(self, name, config):
        self.name = name
        if 'is-prerelease' in config:
            self.is_prerelease = config['is-prerelease']
        if 'prerelease-tag' in config:
            self.prerelease_tag = config['prerelease-tag']
        if 'auto-tag' in config:
            self.auto_tag = config['auto-tag']
        if 'branches' in config:
            branches = config['branches']
            if 'only' in branches:
                self.branch_filter = OnlyBranchFilter(branches['only'])
            elif 'ignore' in branches:
                self.branch_filter = IgnoreBranchFilter(branches['ignore'])

    def get_name(self) -> str:
        return self.name

    def is_matching(self, branch) -> bool:
        return self.branch_filter.is_match(branch)


class RootDefinition:
    name = 'default'
    version: semver.VersionInfo = '1.0.0'
    environments: List[EnvironmentDefinition] = []

    def __init__(self, name, config):
        self.name = name
        if 'version' in config:
            self.version = semver.VersionInfo.parse(config['version'])
        else:
            self.version = semver.VersionInfo.parse('1.0.0')
        if 'environments' in config:
            for name, env in config['environments'].items():
                self.environments.append(EnvironmentDefinition(name, env))

    def get_version(self) -> semver.VersionInfo:
        return self.version

    def get_environment(self, branch_name) -> Optional[EnvironmentDefinition]:
        results: List[EnvironmentDefinition] = []
        for env in self.environments:
            if env.is_matching(branch_name):
                results.append(env)
        if len(results) == 0:
            print(f"No env match the current branch {branch_name}.")
            return None
        if len(results) > 1:
            print(
                f"Multiple env match the current branch {branch_name}. matching env: {list(map(lambda x: x.get_name(), results))}")
        return results[0]


class Config:
    definitions: List[RootDefinition] = []

    def __init__(self, path):
        with open(path) as file:
            try:
                yml = yaml.safe_load(file)
                for name, c in yml.items():
                    self.definitions.append(RootDefinition(name, c))
            except yaml.YAMLError as exc:
                print(exc)

    def get_definitions(self) -> List[RootDefinition]:
        return self.definitions
