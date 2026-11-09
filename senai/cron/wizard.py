"""Sequential terminal wizard; no persistence until an explicit yes."""
from .draft import Destination, build_draft, preview_draft, commit_draft
from .when import parse_when, EXAMPLES


class _Cancelled(Exception):
    pass


def run_wizard(*, project, store_factory, stdin, stdout, clock, timezone, destinations,
               name=None, prompt=None, when=None, recurrence=None):
    if not destinations or not all(isinstance(d,Destination) for d in destinations):
        raise ValueError('No executable delivery destination is configured. Ask setup/coordinator to connect a destination and matching worker/store; nothing was saved.')
    if len({d.key for d in destinations}) != len(destinations):
        raise ValueError('Delivery destination keys must be unique.')
    if not stdin.isatty():
        raise ValueError('Interactive creation needs a terminal. Supply explicit create flags instead.')
    now = clock()

    def ask(label, validate):
        while True:
            print(label, end=' ', file=stdout, flush=True)
            line = stdin.readline(4098)
            if not line:
                raise _Cancelled()
            text = line.strip()
            if text.lower() in ('/cancel','cancel'):
                raise _Cancelled()
            if len(line)>4096:
                raise ValueError('Input is too long; nothing was saved. Keep each answer under 4096 characters.')
            try:
                return validate(text)
            except ValueError as error:
                print(str(error),file=stdout)

    def nonempty(text):
        if not text:
            raise ValueError('Please enter a value, or /cancel.')
        return text

    try:
        print('Create a schedule. Type /cancel at any question to stop without saving.',file=stdout)
        name = name if name is not None else ask('Name:',nonempty)
        prompt = prompt if prompt is not None else ask('Task:',nonempty)
        print('First run examples: '+EXAMPLES,file=stdout)
        at = (parse_when(when,now=now,timezone=timezone) if when is not None else
              ask('First run:',lambda text:parse_when(text,now=now,timezone=timezone)))
        def draft_repeat(text):
            return build_draft(name=name,prompt=prompt,when=at.isoformat(),
                recurrence=text or 'once',destination=destinations[0],now=now,timezone=timezone)
        if recurrence is None:
            draft = ask('Repeat (once, daily, weekly, every 2 hours; Enter=once):',draft_repeat)
        else:
            draft = draft_repeat(recurrence)
        print('Delivery destinations:',file=stdout)
        for index,destination in enumerate(destinations,1):
            print(f'{index}. {destination.label} — {destination.execution_hint}',file=stdout)
        def choose(text):
            if text.isascii() and text.isdecimal() and 1<=int(text)<=len(destinations):
                return destinations[int(text)-1]
            for destination in destinations:
                if text==destination.key:
                    return destination
            raise ValueError('Choose a listed destination number, or /cancel.')
        destination = ask('Destination:',choose)
        draft = build_draft(name=name,prompt=prompt,when=draft.at.isoformat(),
            recurrence=draft.recurrence,destination=destination,now=now,timezone=timezone)
        print(preview_draft(draft),file=stdout)
        def confirm(text):
            if text.lower() in ('yes','y'):
                return True
            if text.lower() in ('no','n'):
                return False
            raise ValueError('Enter yes to save, no to cancel, or /cancel.')
        if not ask('Confirm and save? [yes/no]:',confirm):
            raise _Cancelled()
        confirmed_now = clock()
        parse_when(draft.at.isoformat(),now=confirmed_now,timezone=timezone)
        store = store_factory(project)
        ident = commit_draft(store,draft,project=project,now=confirmed_now,confirmed=True)
        print(f'Saved {draft.name}. {destination.execution_hint}',file=stdout)
        return ident
    except _Cancelled:
        print('Cancelled. Nothing was saved.',file=stdout)
        return None
