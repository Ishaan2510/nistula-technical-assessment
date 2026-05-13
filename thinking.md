# Part 3 — Thinking Questions

---

## Question A — The Immediate Response

**The message the AI sends at 3am:**

> Hi Priya, I'm really sorry about the hot water. I know this is the last thing you needed tonight, especially with guests arriving in the morning.
>
> I've flagged this to our caretaker right now. Someone will be at the villa within 30 minutes to fix it.
>
> I'll send you a follow-up message in 20 minutes with a status update. We will sort this out before your breakfast.

---

**Why this wording:**

The guest is frustrated and it is 3am. The worst thing the AI can do is open with logistics or policy. The first sentence does one job: acknowledge that this is genuinely bad, not just inconvenient. "I know this is the last thing you needed tonight" reflects the specific pressure of the situation (guests arriving for breakfast) rather than a generic apology.

The second paragraph gives a concrete commitment — 30 minutes, someone physical at the villa — not a vague "we will look into it." Specificity is what makes a 3am message feel trustworthy rather than automated.

The follow-up promise in 20 minutes does two things: it gives the guest a clear next touchpoint so they do not feel abandoned, and it creates an internal system trigger (the platform must actually send that follow-up if no human has responded by then).

The phrase "we will sort this out" is a human phrase. It does not sound like a bot. That matters at 3am.

---

## Question B — The System Response Beyond the Message

**What the platform does the moment the complaint comes in:**

1. **Message is classified as `complaint`.** Confidence score is hard-capped below 0.60. Action is set to `escalate`. The reply is drafted by Claude but is not auto-sent — it goes to agent review first. In a complaint at 3am the AI sends the empathy message but a human must approve any follow-up that makes a commitment (like a refund).

2. **Caretaker is notified immediately via WhatsApp.** The platform pushes a formatted alert: guest name, villa, issue description, timestamp. The message is short and actionable — not a summary, just "Villa B1 — no hot water — Priya, guest arriving 7am for breakfast. Please respond now."

3. **Conversation is flagged as `escalated` in the dashboard.** Any agent logged into the dashboard sees a red priority flag. The conversation moves to the top of the queue.

4. **An internal log entry is created** with: complaint type (hot water), property, guest name, reservation ID, timestamp, and current resolution status.

5. **30-minute timer starts.** If no human acknowledgment (caretaker reply or agent action in dashboard) within 30 minutes, the platform escalates up the chain: notifies the on-call property manager and sends a separate alert to the founder's WhatsApp. The guest receives the 20-minute follow-up message — either a human-written update if someone has responded, or an automated holding message: "Our team is on the way. We have not forgotten you."

6. **If the issue is resolved within 1 hour:** the caretaker marks it resolved in the system. The platform logs resolution time. The guest receives a closing message from the agent confirming the fix.

7. **If the issue is not resolved within 1 hour:** a compensation flag is raised. The system suggests a prorated refund for that night to the agent for approval. No refund is issued automatically — a human must authorise it.

---

## Question C — What the System Does With the Pattern

**The situation:** Third complaint about hot water at Villa B1 in two months. This is not a guest problem. This is a maintenance problem.

**What the system should do with this information:**

The platform should maintain a complaints table indexed by (property, complaint_category). When the same category fires at the same property more than once within a 60-day window, a recurring issue flag is raised. On the third occurrence, an alert goes to the property manager: "Hot water at Villa B1 has been reported by 3 guests in 60 days. This is a maintenance issue, not a guest issue."

**What I would build to prevent a fourth complaint:**

A pre-stay checklist system. Every property has a configurable checklist that runs 24 hours before each new check-in. For Villa B1, after the second hot water complaint, "verify hot water boiler" is added to that checklist automatically. The caretaker receives this checklist on WhatsApp the morning before the guests arrive. They are required to tick off each item before check-in. Non-response triggers a reminder.

The key insight is that the platform already knows the check-in schedule from the reservations table. Connecting that to a caretaker task dispatch is a small build — one cron job, one WhatsApp message template, one acknowledgment flow. But it closes the loop between what guests experience and what operations actually does before the next guest arrives.

Beyond the checklist: after three complaints, the property's health score in the dashboard drops. This does not block bookings automatically, but it requires a manual sign-off from the property manager before the next booking is confirmed. That is a forcing function. It makes the pattern visible to the human who can actually fix the boiler.

The complaint data also feeds the conversation intelligence layer. Over time, if you have 20 properties and 18 months of complaint data, you can start to see seasonal patterns (hot water failures in monsoon, AC failures in summer), property-specific failure modes, and caretaker response time distributions. That is when preventive maintenance scheduling becomes genuinely data-driven rather than reactive.