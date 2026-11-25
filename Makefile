PY ?= python3
P = $(PY) pipeline

.PHONY: film radio validate smoke narration keyframes refs shots music assemble setup clean-final

## make film: run the whole pipeline end to end (only changed shots are regenerated)
film: validate narration keyframes shots music assemble

## make radio: narration + temp music on black, for the first user test
radio: validate narration music
	$(P)/assemble.py --radio

setup:
	$(PY) -m pip install -r requirements.txt

validate:
	$(P)/validate.py

smoke:
	$(P)/smoke_test.py

narration:
	$(P)/narration.py

refs:
	$(P)/keyframes.py --refs-only

keyframes:
	$(P)/keyframes.py

shots:
	$(P)/shots.py

music:
	$(P)/music.py

assemble:
	$(P)/assemble.py

clean-final:
	rm -rf outputs/final
