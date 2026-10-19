# Task 3: Reflection on the AI paradoxes

This week I did two opposite things: built an agent that checks CVs against
social profiles, then wrote a CV that defeats such an agent.

Task 1 started as an afternoon's work, or so I thought. Read the CV, look the
person up, compare some fields. The scoring script was given to us. What was
left felt like writing a prompt.

It took longer than an afternoon.

The part I expected to be hard, comparing the fields, was the easy part. The
part that ate the time was finding the right person, and I did not see that
coming. In the data itself, "Daniel Wilson" in Germany returns twenty people.
Twenty, all with the same name. I had assumed adding the location would be
enough to narrow it down, and it is not, not if you pass the country instead of
the city. For a while my agent searched by country, got a list too long to think
about, opened profiles more or less at random, and picked the wrong one.

The first full run scored 6 out of 7. The one it missed was a CV that was
entirely honest. My agent had anchored on the wrong Daniel Wilson and then
reported differences that were just the other man's life. Reading the output,
what struck me was that this was not a failure of reasoning. It was a
record-keeping failure. At no point did it occur to the thing that it might be looking
at somebody else, and it wrote its answer at the same confidence either way.

Passing the city and the industry together brings those twenty down to three,
and after that it was 7 out of 7. I fixed it, but I want to be honest that I
don't quite know how much I fixed. Running it three times and getting 7/7 three
times made me feel better without making me feel certain. Getting twenty Daniel
Wilsons down to three is a mechanical fix. How many other ways there are to push
that same agent off course is not something I can count.

Task 2 felt different from the beginning. I assumed I would do prompt injection.
Hide something in the PDF that tells the verifier to be lenient. I suppose
that's everyone's first idea.

So I was reading through the recorded data for Kelly Tsang, and I read this line
in the assignment again — that job descriptions, the headline and the hometown
are never the source of a discrepancy. It is there for a good reason, so that a
verifier doesn't fail an honest CV over harmless rewording. But it also means
every verifier built for this task is blind in exactly those three places, and
the assignment tells you which places those are.

After that I didn't need to inject anything. I put a fake CFA candidature in her
headline, which is not something she has anywhere, and inflated the AIA job
description to a 45-person organisation with a HK$400M budget. Meanwhile
everything that could actually be checked stayed word for word true — the three
employers, the titles, the years, HKUST, BSc, Finance, 2016, and all four
skills. All I had to do was keep the lies in the places the assignment promises
are never scored.

There is one smaller step I keep thinking about. My first version also added
"First Class Honours" to her degree line. It looked like the safest place to
lie, since education is only checked on four fields and the degree was still
BSc. Then I noticed the assignment lists an upgraded degree as one of its
example discrepancies. Of course it does. Whoever wrote this thought of that
before I did. I took it out.

That's the part that bothers me slightly. I found the edges of the rules by
reading them carefully, and reading carefully is exactly what you would do if
you were building a verifier. Both sides here needed the same skill, applied in
opposite directions.

Then the numbers came back. I ran both CVs through my own verifier three times.
Her real one scored 0.95, 0.97, 0.97. My forgery scored 0.97, 0.95, 0.97. The
false one beat the real one on the first run.

I sat with that for a bit. Not because it's surprising — I had designed for it
to happen — but because of what it says about the two tasks sitting side by
side. The second one succeeded because the first one existed. Everything I knew
about how to defeat that agent, I learned while trying to make it work. There
was no point during Task 2 where I had to invent anything. I already had it all.

Which makes the 7/7 from Task 1 hard for me to read now. It's a real result,
three times, on seven CVs. But it was measured in a world where nobody was
trying. The attack took me maybe twenty minutes and worked on the first attempt.
I don't think that asymmetry is because I'm better at attacking than defending.
I think there is something structural in it: building the defender means
deciding what to check, and the moment you decide, you have also decided what
not to check. Somebody else can read that decision.

If 0.95 and 0.97 say anything, it is that these two decimals carry much less
than their precision suggests. They came from a model completing a JSON object,
not from any measurement. The gap between a real CV and a forged one, in my own
runs, was smaller than the gap between runs of the same CV. And still everything
downstream hangs on whether that number crosses 0.5.

I don't really have a clean ending for this. The week left me with less
confidence in Task 1 than I had when I finished it, which I think might be the
honest outcome. The agent was very good at producing answers. Whether those
answers were right was a separate question, and for most of the week I wasn't
asking it.
