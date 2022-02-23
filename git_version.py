import semver
from typing import Optional
from git import Repo, TagReference
from config import RootDefinition, EnvironmentDefinition


class GitVersion:
    definition: RootDefinition
    repo: Repo
    auto_push: bool

    def __init__(self, repo: Repo, definition: RootDefinition, auto_push: bool):
        self.repo = repo
        self.definition = definition
        self.auto_push = auto_push

    def __tag_current_branch(self, version: semver.VersionInfo) -> None:
        tag = self.repo.create_tag(f'{self.definition.name}-{version}',
                                   message=f'{self.definition.name} version {version}')
        if self.auto_push:
            self.repo.remotes.origin.push(tag)

    def __prerelease_tag(self, env: EnvironmentDefinition, prerelease_number: int):
        if env.prerelease_tag is None:
            return f'{self.repo.active_branch.name}.{prerelease_number}'
        return f'{env.prerelease_tag}.{prerelease_number}'

    def get_new_version(self, build_number: Optional[int]) -> semver.VersionInfo:
        branch_name = self.repo.active_branch.name
        env = self.definition.get_environment(branch_name)
        latest_tag = self.__find_latest_stable_tag()
        latest_version = self.__find_latest_version(latest_tag)
        # todo replace by searching if commit have tag -> Remove
        if latest_tag is not None and latest_tag.commit == self.repo.active_branch.commit:
            return latest_version
        current_version: semver.VersionInfo
        if latest_version is None or self.definition.version.compare(latest_version) == 1:
            current_version = self.definition.version
        else:
            current_version = latest_version

        if env.is_prerelease:
            return self.__prerelease_version(latest_tag, latest_version, env, current_version, build_number)
        else:
            return self.__stable_version(latest_tag, latest_version, env, current_version, build_number)

    def __prerelease_version(self,
                             tag: Optional[TagReference],
                             tag_version: semver.VersionInfo,
                             env: EnvironmentDefinition,
                             version: semver.VersionInfo,
                             build_number: Optional[int]) -> semver.VersionInfo:
        if tag_version.compare(version) == 0:
            version = version.bump_patch()
        c: int
        if tag is not None and tag.commit == self.repo.active_branch.commit:
            c = 0
        else:
            c = self.__count_commit_since(tag)

        return semver.VersionInfo(version.major,
                                  version.minor,
                                  version.patch,
                                  self.__prerelease_tag(env, c),
                                  str(build_number) if build_number is not None else None)

    def __stable_version(self,
                         tag: Optional[TagReference],
                         tag_version: semver.VersionInfo,
                         env: EnvironmentDefinition,
                         version: semver.VersionInfo,
                         build_number: Optional[int]) -> semver.VersionInfo:
        if tag is None:
            return semver.VersionInfo(version.major,
                                      version.minor,
                                      version.patch,
                                      str(build_number) if build_number is not None else None)
        return semver.VersionInfo(version.major,
                                  version.minor,
                                  version.patch + 1,
                                  str(build_number) if build_number is not None else None)

    def tag_current_commit(self, version: semver.VersionInfo):
        branch_name = self.repo.active_branch.name
        env = self.definition.get_environment(branch_name)
        def_name = self.definition.name
        tag_current_commit = next(
            (t for t in self.repo.tags if t.commit == self.repo.active_branch.commit and t.name.startswith(def_name)),
            None)
        if env.auto_tag and tag_current_commit is None:
            self.__tag_current_branch(version)

    def __count_commit_since(self, tag: Optional[TagReference]) -> int:
        count = 0
        commit = None
        if tag is not None:
            commit = tag.commit
        for c in self.repo.iter_commits(rev=self.repo.active_branch.commit):
            if commit is not None and c == commit:
                break
            count += 1
        return count

    def __find_latest_stable_tag(self) -> Optional[TagReference]:
        tags = self.repo.tags
        def_name = self.definition.name

        def tag_filter(x: TagReference) -> bool:
            if not x.name.startswith(def_name):
                return False
            name = x.name[len(def_name) + 1::]
            v = semver.VersionInfo.parse(name)
            return v.finalize_version() == v

        filtered_tags = list(filter(tag_filter, tags))
        filtered_tags = list(sorted(filtered_tags, key=lambda x: x.commit.committed_date))
        if len(filtered_tags) == 0:
            return None
        tag = filtered_tags[len(filtered_tags) - 1]
        return tag

    def __find_latest_version(self, tag: Optional[TagReference]) -> Optional[semver.VersionInfo]:
        if tag is None:
            return None
        def_name = self.definition.name
        tag_name = tag.name[len(def_name) + 1::]
        return semver.VersionInfo.parse(tag_name)
