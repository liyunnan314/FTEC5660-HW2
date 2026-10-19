# Reflection: Six Ironies I Ran Into Building a KYC Agent and Then Breaking It

This homework asked me to do two opposite things in sequence: build an agent that
checks CVs against social profiles, then write a CV that defeats such an agent.
The second task succeeded much more cleanly than I expected, and that success is
what I keep coming back to. Below are six things that struck me, mostly because
they were things I did not expect and could not have reasoned my way to in
advance.

## 1. My attack worked because the specification told me exactly where to aim

The surprising part is that my CV beat the verifier without exploiting a single
bug in it. It exploits the *rules*. Section 3.1 states that discrepancies live in
name, city, jobs, education and skills, and that "job descriptions, the headline
and the hometown are never the source of a discrepancy". That sentence exists so
that honest differences in phrasing are not punished. But it also draws a map of
everywhere a verifier is forbidden to look, so I put a fake CFA candidature in
the headline and inflated some job descriptions, and left every checkable field
untouched.

The irony is uncomfortable: **the more faithfully a verifier implements the spec,
the more predictably it can be defeated.** Perfect compliance produces perfect
predictability, and predictability is the attacker's raw material. Any SEC Rule
ever written and any KYC checklist behaves this way — publish the audit criteria
and you have published the evasion manual for everything just outside them. This
is Goodhart's law wearing a compliance badge: once checking becomes the target,
the unmeasured remainder is where the truth goes to hide.

## 2. The defender's knowledge and the attacker's are the same knowledge

I could only write that CV because I had spent hours debugging the verifier. I
knew which fields got compared, which searches were run, which differences were
forgiven. Nothing about the attack required cleverness that I did not already
possess from the defensive side.

That should be worrying for anyone deploying this for real. A bank fielding a KYC
agent holds exactly the asset a fraudster wants: the list of what gets checked.
That list leaks cheaply and continuously — through rejected applications, through
the shape of an agent's output, through staff, through watching what the agent
asks follow-up questions about. My Task 2 write-up is honest about having walked
away from prompt injection, and even that reasoning is useful to an attacker. I
am not sure there is a fix for this; there is only the recognition that shipping a
verifier also ships information.

## 3. The thing I could not predict was the thing that nearly broke Task 1

Task 1's first run scored 6/7, and the loss was not a failure of reasoning. The
agent had searched `Daniel Wilson` in Germany, found twenty namesakes, opened ten
profiles, and anchored on the wrong person — inventing discrepancies in a CV that
was entirely truthful. Searching by city *and* industry instead cut twenty
candidates to three and fixed it.

So the agent handles what a human would call the hard part — entity resolution
across hundreds of people, cross-referencing two platforms, comparing fields —
reasonably well. What trips it is the part nobody would call hard: reading two
numbers sitting on one line of a PDF.

That is Moravec's paradox in its modern form, and it has a sting in the tail. We
cannot predict, by thinking about it, where an agent will fail, because the
boundary between easy and hard does not match our intuition at all. Which means
**human oversight is not the safety net it is assumed to be** — we do not know
where to keep our attention, and the failures arrive in places we were not
looking.

## 4. Two decimal places bought more trust than they deserved

My agent emits scores like 0.97 and 0.95. Over three runs the falsified CV drew
0.97 / 0.95 / 0.97 and the genuine one drew 0.95 / 0.97 / 0.97:

```
genuine CV      ████████████████████░  0.95
falsified CV    █████████████████████  0.97      ← decides nothing

genuine CV      █████████████████████  0.97
falsified CV    ████████████████████░  0.95      ← decides nothing
```

Those numbers came out of a language model completing JSON. They are not
calibrated probabilities, they carry no error bars, and the gap between them is
smaller than the noise between runs. Yet everything downstream treats 0.5 as a
line that decides whether a person is trustworthy.

The perverse incentive is that **making the output more precise makes the system
less safe**, because it becomes harder for a human reviewer to argue with and
easier to rubber-stamp. A verifier that said "these fields match, these three I
could not check, and I cannot distinguish two namesakes" would be less
impressive and far more honest.

## 5. Automation moves the need for judgement to the worst possible moment

Task 1 exists to remove a human from the loop. Suppose it works and the human
reviewer becomes a rubber stamp. The irony described by Bainbridge in 1983 still
holds: automation does not remove the need for human judgement, it relocates that
need to exactly when it has been hollowed out. By the time something genuinely
unusual arrives — my CV, in this analogy — the reviewer has spent months seeing
cases the agent handles well, has lost the practice of suspicion, and is least
equipped at the moment that matters most. In KYC that moment is not a curiosity;
it is a sanctioned account or a laundering channel.

## 6. Making screening cheaper raises the total amount of screening

The same generative tooling that made my verification agent cheap also makes it
cheap to produce polished, individually tailored, statistically optimised CVs at
scale. Lowering the cost of screening does not reduce the workload; it invites
more attempts and raises the amount of checking demanded. Efficiency gains here
do not settle into the system as savings, they are converted into a more intense
game. I got a small preview of that arms race in an afternoon.

---

## What I would actually change

The honest conclusion is that my best work this week invalidated my worst work,
and both came from the same knowledge. If I were taking this to production rather
than submitting it:

- **Stop treating pass rate as a security measure.** An adversarial score belongs
  next to the accuracy score, every release.
- **Treat the check list as part of the threat model.** What is not examined is
  not neutral, it is an invitation, and the list should not be treated as public
  documentation.
- **Buy unpredictability rather than stricter menus.** Randomised and varied
  checking paths cost more but give an attacker nothing stable to optimise
  against.
- **Make human review meaningful or remove it.** Reviewers should be given cases
  where they form a view *before* seeing the agent's verdict, otherwise the
  verdict simply becomes the answer.
- **Prefer calibrated uncertainty to confident numbers.** "Unknown" being
  representable is worth more than a second decimal place.

What I am left with is less certainty than I started the week with, and I think
that is probably the correct outcome. The agent was very good at producing
answers. Whether those answers meant anything depended on things I could not see
from inside it, and for most of the week I did not know that I should be asking.
