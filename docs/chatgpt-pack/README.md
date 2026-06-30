# ChatGPT paste-only pack

## Setup (one-time)
1. Open ChatGPT webUI → Settings → Personalization → Custom instructions
2. Copy the contents of `custom-instructions.txt` into the "What would you like ChatGPT to know?" field
3. Save

## Usage
- At session start: ask Ryan for `convmem brief --stdout-only`
- At session close: suggest `convmem record` blocks for Ryan to run

## Notes
- ChatGPT cannot run CLI commands — never pretend to call convmem
- Session-close record blocks use the format in `docs/inter-model/SESSION-CLOSE-RECORD.md`
