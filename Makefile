PY ?= python3
P = $(PY) pipeline
V = $(PY) pipeline/validators.py

.PHONY: film radio validate script smoke narration keyframes refs shots music assemble check setup clean-final

## make film: every stage, each followed by its validator (a FAIL stops the run)
film: validate script narration keyframes shots music assemble

## make radio: narration + temp music on black, for the first user test
radio: validate narration music
	$(P)/assemble.py --radio

## make check: run every validator on the current outputs (add V_ARGS=-v to see each PASS)
check:
	$(V) all $(V_ARGS)

setup:
	$(PY) -m pip install -r requirements.txt

validate:
	$(P)/validate.py
	$(V) storyboard

script:
	$(P)/script.py
	$(V) script

smoke:
	$(P)/smoke_test.py

narration:
	$(P)/narration.py
	-$(P)/narration_check.py
	$(V) narration

refs:
	$(P)/keyframes.py --refs-only

keyframes:
	$(P)/keyframes.py
	$(V) keyframes

shots:
	$(P)/shots.py
	$(V) shots

music:
	$(P)/music.py
	$(V) music

assemble:
	$(P)/assemble.py
	$(V) assemble

clean-final:
	rm -rf outputs/final
