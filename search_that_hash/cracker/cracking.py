from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor


from loguru import logger

from search_that_hash import printing

from search_that_hash.cracker.offline_mod import hashcat
from search_that_hash.cracker.online_mod import online

class Searcher:
    def __init__(self, config):
        self.config = config
        self.searchers_offline = [hashcat.Hashcat()]
        self.searchers_online = [
            online.md5crypt(),
            online.rainbow_tabels(),
            online.nitrxgen(),
            online.cmd5(),
            online.LmRainbowTabels(),
            online.md5_addr(),
            online.md5_grom(),
            online.sha1_grom(),
            online.hashsorg(),
        ]
        self.Hash_input = namedtuple(
            "Hash_input",
            [
                "text",
                "types",
                "hashcat_types",
                "api_keys",
                "timeout",
                "greppable",
                "wordlist",
                "binary",
                "api",
            ],
        )

    def main(self):

        return self.perform_search(self.config)

    def perform_search(self, config):

        out = []

        if not config["timeout"]:
            config["timeout"] = 1

        for hash, types in config["hashes"].items():
            hash_ctext = hash

            keys = [type["name"].lower() for type in types]
            hashcat_types = [type["hashcat"] for type in types]
            supported_searchers = []
            types = []

            if not config["offline"]:
                for search in self.searchers_online:
                    for hashtype in keys:
                        if hashtype.lower() in search.supports:
                            if not search in supported_searchers:
                                supported_searchers.append(search)
                            if not hashtype in types:
                                types.append(hashtype)
            supported_searchers.append(hashcat.Hashcat())
            """if config["hashcat"]:
                
            else:
                supported_searchers.append(offline.john())  # Offline searchers"""

            future = self.Hash_input(
                hash_ctext,
                types,
                hashcat_types,  # For john, hashcat
                # TODO don't update config like this, use the config updater file pls
                config["api_keys"],
                config["timeout"],
                config["greppable"],
                config["wordlist"],
                config["binary"],
                config["api"],
            )

            out.append(self.threaded_search(future, supported_searchers))

        return out

    def threaded_search(self, future, supported_searchers):

        processes = []
        success = {}
        fails = {}

        with ThreadPoolExecutor(max_workers=6) as executor:
            for search in supported_searchers:
                processes.append(executor.submit(self.call_searcher, search, future))
                for (
                    possible_done
                ) in processes:  # Checks the progress of everything during cracking
                    if possible_done in success or possible_done in fails:
                        continue

                    if (
                        list(possible_done.result().values())[0] == "Failed"
                        or list(possible_done.result().values())[0] == "Not connected"
                    ):
                        fails.update(possible_done.result())
                    else:
                        success.update(possible_done.result())

                        if not future[
                            5  # Checks if greppable, if not then skips goes fast, if yes then returns and prints JSON.
                        ]:  # Prints without waiting for other threads to finish.

                            if not future[8]:
                                printing.Prettifier.one_print(
                                    str(list(possible_done.result().values())[0]),
                                    future[0],
                                )
                            return {
                                future[0]: str(list(possible_done.result().values())[0])
                            }

        return {future[0]: [success, fails]}

    def call_searcher(self, search, future):
        try:
            return {type(search).__name__: search.crack(future)}
        except Exception as e:
            return {type(search).__name__: "Failed"}