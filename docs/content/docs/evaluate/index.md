# Overview

An evaluation framework runs your [agent](/docs/concepts#agent) on a fixed set of test cases, measures every run and shows how well the agent does its job. It turns "the answers looked fine in a few chats" into pass rates, costs and a list of the cases that failed, which you can compare from one change to the next.

## Why evaluate your agents

An agent's behavior depends on many moving parts: its prompt, the language model, its tools, the data it searches and the code of its [domain definition](/docs/concepts#domain-definition). A change to any of them can make the agent better on one kind of request and worse on another, and a language model answers a little differently every time. Trying a handful of questions by hand catches the obvious problems and misses the rest.

Take the nutrition assistant from the [tutorial](/docs/customization/tutorial), which plans meals around each user's allergies and calorie target. You rewrite its prompt to make the plans more varied, and the first few plans you try look better. An evaluation runs the same thirty users through the assistant before and after the change and shows the full picture:

- the pass rate drops from 96% to 88%,
- two of the failed plans contain peanuts for a user with a peanut allergy,
- the agent now needs twice as many recipe searches per day, and each plan costs 40% more.

With that in front of you, you keep the variety, fix the allergy handling and run the evaluation again before the change reaches your users. The same comparison answers other everyday questions: whether a cheaper model is good enough, whether a new tool helps, or whether an update to the data broke something.

## What Suvereo gives you

If you want to evaluate your agents, Suvereo has you covered. Evaluation is built in and runs the same agents, [agentic executions](/docs/concepts#agentic-execution) and [conversations](/docs/concepts#conversation) your users rely on:

- **Suites you keep with your code.** A suite is a few plain files: which agent to run, with which models and prompts, the test cases, and what to measure. It lives next to your domain definition and changes with it.
- **Checks on what the agent produced and how it worked.** Metrics compare the agent's answer with the expected one, count the tools it called and the order it called them in, and let a judge model grade what takes judgment, such as whether every search respected the user's allergies.
- **Conversations with simulated users.** Chat agents are tested over whole dialogues, with fixed messages or with a simulated user that has a goal, a persona and the facts it knows.
- **Mocks for external systems.** A run can work on fixture data and answer calls to a shop or another API from the suite, so the results repeat run after run and the real systems stay untouched.
- **Side-by-side comparison.** Every model and prompt variant gets its own pass rate, cost and failures in one report, with a diff against an earlier run and a history of every run.
- **Ready for CI.** A spending limit caps every run, repeats show which cases are flaky, and the exit code tells your pipeline whether the agent still meets its pass rate.

## Where to go next

[Evaluate an Agent](./evaluate-an-agent) walks through a first suite for the tutorial's nutrition assistant, from the test cases to reading the report.
