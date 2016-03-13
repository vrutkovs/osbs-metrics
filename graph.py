from collections import defaultdict
import json
from osbs.utils import strip_registry_from_image
import sys


class BuildTree(object):
    def __init__(self, builds):
        self.deps = defaultdict(set)
        self.seen = set()
        builds.sort(key=lambda x: x['metadata']['creationTimestamp'],
                    reverse=True)
        for build in builds:
            self.add(build)

    def add(self, build):
        try:
            annotations = build['metadata']['annotations']
            base_image_name = annotations['base-image-name']
            repositories = json.loads(annotations['repositories'])
        except KeyError:
            return

        repos = [strip_registry_from_image(repo)
                 for repos in repositories.values()
                 for repo in repos]
        duplicates = self.seen.intersection(repos)
        if duplicates:
            return

        self.seen.update(repos)
        self.deps[strip_registry_from_image(base_image_name)].update(repos)

    def _trim_layers(self, base):
        layers = self.deps[base]
        excess = set()
        for layer in layers:
            name, version = layer.split(':', 1)
            if version == 'latest':
                pass
            elif layer not in self.deps:
                # Leaf node
                excess.add(layer)

        self.deps[base] = list(set(layers) - excess)

    def trim_excess_tags(self):
        images = [image for image in self.deps.keys()]
        for base in images:
            if base in self.deps:
                self._trim_layers(base)

    def __repr__(self):
        return repr(self.deps)


def run(inputfile):
    with open(inputfile) as fp:
        builds = json.load(fp)

    from pprint import pprint
    tree = BuildTree(builds)
    tree.trim_excess_tags()
    pprint(tree.deps)


if __name__ == '__main__':
    run(sys.argv[1])
