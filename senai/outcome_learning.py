"""Trusted app evidence -> conservative noteworthy evaluator -> learning decisions.

No model output, uploaded JSON, observation history or repetition grants confirmation.
Checks are supplied by application code, never extracted from requests or responses.
"""
from dataclasses import dataclass
import hashlib
import re
import subprocess
from .memory import MemoryEvent, evaluate_noteworthy
from .memory.store import validate_text

PERSONAL=("preference","habit","like","dislike","choice")

@dataclass(frozen=True)
class MilestoneCheck:
    event_id: str
    text: str
    command: tuple[str,...]
    significant: bool=False
    timeout: float=30

class OutcomeLearning:
    def __init__(self,memory,*,confirm=None,checks=(),runner=subprocess.run):
        self.memory,self.confirm,self.checks,self.runner=memory,confirm,tuple(checks),runner
        if len(self.checks)>99:raise ValueError("Too many milestone checks.")
        for check in self.checks:
            if not isinstance(check,MilestoneCheck):raise ValueError("Trusted checks required.")
            validate_text(check.event_id,"event ID",200)
            validate_text(check.text,"milestone",240)
            if (type(check.significant) is not bool or not isinstance(check.command,tuple)
                or not check.command or not all(isinstance(v,str) and v for v in check.command)
                or not 0<check.timeout<=300):
                raise ValueError("Invalid trusted milestone check.")

    def __call__(self,request,response,workspace):
        from .memory_runtime import LearningDecision
        events=[]
        text=request.rsplit("\n\nUser message:\n",1)[-1].strip()
        explicit=re.fullmatch(r"remember my (preference|habit|like|dislike|choice):\s*(.+)",
                              text,re.I)
        observation=re.fullmatch(r"my (preference|habit|like|dislike|choice):\s*(.+)",text,re.I)
        if explicit or observation:
            match=explicit or observation
            kind,fact=match[1].lower(),match[2]
        else:
            match=re.fullmatch(r"I (prefer|like|dislike) .+",text,re.I)
            kind={"prefer":"preference","like":"like","dislike":"dislike"}.get(match[1].lower()) if match else None
            fact=text
        if kind:
            try:fact=validate_text(fact,"candidate",240)
            except ValueError:fact=None
            if fact and not any(c in fact for c in "\n\r\t"):
                event=MemoryEvent("user:"+hashlib.sha256(text.encode()).hexdigest(),kind,fact,
                                  "user",verified=True,significant=kind=="choice")
                confirmed=bool(explicit) or (self.confirm is not None and self.confirm(event) is True)
                events.append(MemoryEvent(event.event_id,kind,fact,"user",verified=True,
                                          confirmed=confirmed,significant=event.significant))
        for check in self.checks:
            if not check.significant:continue
            try:
                result=self.runner(list(check.command),cwd=workspace,stdin=subprocess.DEVNULL,
                    capture_output=True,text=True,timeout=check.timeout,check=False)
                verified=type(result.returncode) is int and result.returncode==0
            except (OSError,subprocess.SubprocessError):
                verified=False
            events.append(MemoryEvent("validator:"+check.event_id,"milestone",check.text,
                                     "validator",verified=verified,significant=True))
        existing={name:self.memory.profiles.read(name).text for name in ("USER.md","MEMORY.md")}
        by_id={event.event_id:event for event in events}
        decisions=[]
        for proposal in evaluate_noteworthy(events,existing=existing):
            event=by_id[proposal.evidence_id]
            decisions.append(LearningDecision(proposal.name,proposal.text,
                noteworthy=True,verified=True,confirmed=event.confirmed,
                kind=event.kind,source=event.source,significant=event.significant))
        return decisions
