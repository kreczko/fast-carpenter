"""
Functions to run a job using alphatwirl
"""

from atuproot.BEvents import BEvents
from ..masked_tree import MaskedUprootTree
from .. import dataspace

class EventRanger():
    def __init__(self):
        self._owner = None

    def set_owner(self, owner):
        self._owner = owner

    @property
    def start_entry(self):
        return (self._owner.start_block + self._owner.iblock) * self._owner.nevents_per_block

    @property
    def stop_entry(self):
        i_block = min(self._owner.iblock + 1, self._owner.nblocks)
        stop_entry = (self._owner.start_block + i_block) * self._owner.nevents_per_block
        return min(self._owner.nevents_in_tree, stop_entry)

    @property
    def entries_in_block(self):
        if self._owner and self._owner.iblock > -1:
            return self.stop_entry - self.start_entry
        return None


class BEventsWrapped(BEvents):
    def __init__(self, ds, *args, **kwargs):
        ranges = EventRanger()
        # TODO: include ranges to dataspace
        super(BEventsWrapped, self).__init__(ds, *args, **kwargs)
        ranges.set_owner(self)

    def _block_changed(self):
        # TODO: Do we need to reset the mask/cache here?
        # block changes should be injected --> self.tree.blockchange()
        # self.tree.reset_mask()
        # self.tree.reset_mask()
        # self.tree['input_trees'].notify(actions=['reset_mask', 'reset_cache'])
        self.tree.reset_mask()

    def __getitem__(self, i):
        result = super(BEventsWrapped, self).__getitem__(self, i)
        self._block_changed()
        return result

    def __iter__(self):
        for value in super(BEventsWrapped, self).__iter__():
            self._block_changed()
            yield value
        self._block_changed()


class EventBuilder(object):
    def __init__(self, config):
        self.config = config

    def __repr__(self):
        return '{}({!r})'.format(
            self.__class__.__name__,
            self.config,
        )

    def __call__(self):
        ds = dataspace.from_file_paths(self.config.inputPaths, self.config.treeName)
        events = BEventsWrapped(ds,
                                self.config.nevents_per_block,
                                self.config.start_block,
                                self.config.stop_block)
        events.config = self.config
        return events


class DummyCollector():
    def collect(self, *args, **kwargs):
        pass


class AtuprootContext:
    def __enter__(self):
        import atuproot.atuproot_main as atup
        self.atup = atup
        self._orig_event_builder = atup.EventBuilder
        self._orig_build_parallel = atup.build_parallel

        from atsge.build_parallel import build_parallel
        atup.EventBuilder = EventBuilder
        atup.build_parallel = build_parallel
        return self

    def __exit__(self, *args, **kwargs):
        self.atup.EventBuilder = self._orig_event_builder
        self.atup.build_parallel = self._orig_build_parallel


def execute(sequence, datasets, args):
    """
    Run a job using alphatwirl and atuproot
    """

    if args.ncores < 1:
        args.ncores = 1

    sequence = [(s, s.collector() if hasattr(s, "collector") else DummyCollector()) for s in sequence]

    with AtuprootContext() as runner:
        process = runner.atup.AtUproot(args.outdir,
                                       quiet=args.quiet,
                                       parallel_mode=args.mode,
                                       process=args.ncores,
                                       max_blocks_per_dataset=args.nblocks_per_dataset,
                                       max_blocks_per_process=args.nblocks_per_sample,
                                       nevents_per_block=args.blocksize,
                                       profile=args.profile,
                                       profile_out_path="profile.txt",
                                       )

        ret_val = process.run(datasets, sequence)

    if not args.profile:
        # This breaks in AlphaTwirl when used with the profile option
        summary = {s[0].name: list(df.index.names) for s, df in zip(sequence, ret_val[0]) if df is not None}
    else:
        summary = " (Results summary not available with profile mode) "

    return summary, ret_val
