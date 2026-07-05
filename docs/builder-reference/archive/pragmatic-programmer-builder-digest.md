# Pragmatic Programmer — appendix notes

**Source:** *The Pragmatic Programmer* (2nd ed.) · Topic 3 (Software Entropy / Broken Windows) pp. 42–43, Topic 12 (Tracer Bullets) pp. 109–117

Two short sections directly relevant to convmem's build discipline. Not a full digest — the rest of the book covers principles already practiced in this repo.

## Tracer Bullets (pp. 109–117)

The tracer bullet metaphor: instead of specifying every requirement upfront, build a minimal end-to-end skeleton that works in the real environment, then iterate. The skeleton is not a prototype — it's lean but complete, and it stays.

Convmem's decision pipeline was built this way: propose → review → approve → index was the first tracer bullet. Everything since (verify scripts, builder-reference deploy, MCP read-only gate) is iterative refinement on that skeleton.

Key distinction from prototyping (Topic 13, p. 117): prototypes generate disposable code; tracer code is kept and evolved. If you build a feature as a spike and intend to rewrite it, that's a prototype. If you build the minimal working version and intend to extend it, that's tracer code.

## Don't Live with Broken Windows (pp. 42–43)

The broken windows theory applied to software: one known defect left unfixed leads to more. A stale protocol file, a hand-edited surface file, a digest that claims to cover a chapter it doesn't — each is a broken window.

Convmem's protocol generation SSoT and builder-reference deploy scripts are the enforcement mechanism: if a surface file drifts, the verifier fails. That's the pragmatic response to broken windows — make them structurally impossible rather than relying on discipline.

## Usage

These two sections are best referenced as context for build-philosophy discussions rather than loaded as a standalone digest. The rest of the Pragmatic Programmer's principles (DRY, orthogonality, Design by Contract) are already well-covered by the Ousterhout and Hard Parts digests at higher density.
