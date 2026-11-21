# What does the last movement add once the latest spikes are known?

At the start of bin *k*+10, the experiment has another 100 ms of arm motion and cortical spikes. This model sees the preceding 200 ms of counts on its **own contact** and the next 100 ms of counts, in six 50-ms groups. It also sees the earlier arm and cue state. Adding the measured displacements at *k*+4 and *k*+9 yields the updated forecast. Its target is the positive-sort spike total over *k*+10 through *k*+19. The 17-contact sensitivity in the pooled-count study uses that same target with a different predictor: counts from the earlier history on 37 contacts and the movement residual at one time point.

September 7 supplied 22 contacts with positive sorts. Seventeen shared that coverage on both physical blocks of September 14. Fifteen kept the same number of positive sorts. Counts at contact 15 went from two sorts to one and contact 53 went from one to two. The full results give the common, equal, growing and shrinking groups separately.

| Workspace | Measured movement minus stale position | Measured movement minus another reach's movement |
|---|---:|---:|
| 1 | +0.004 [−0.019, +0.029] | −0.102 [−0.144, −0.059] |
| 2 | +0.096 [+0.013, +0.193] | +0.008 [−0.108, +0.107] |

Each cell gives the change in original-balanced mean Poisson deviance and its 95% moving-block interval. Stale position keeps the recent spikes. The other-reach control substitutes displacement only. The model missed the criterion that both comparisons have an upper bound below zero in each workspace. The score file includes measured update, stale position, earlier-only, movement-only, wrong donor, zero displacement, late and early count persistence, and the training mean. It also reports contact yield, assigned trials, donor gaps and independent-trial intervals. [Full numerical results](results.json)

Each contact and each of the four fitted arms uses its own original-balanced Poisson regression with a log link. The fit standardizes its inputs on the training trials, clips them at ±8, and penalizes squared non-intercept weights at 0.025. A contact-specific earlier mean supplies the intercept initialization. Four chronological holdbacks within September 7 checked the fits before transfer. [September 7 fit](fit.py) · [Frozen specification](frozen.json) · [September 14 scoring](score.py)
