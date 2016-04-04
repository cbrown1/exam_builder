example:
	mkdir -p build/Unit1
	mkdir -p out/Unit1
	python exam_builder.py src/exam_1.yml -o build/Unit1/Exam.md -t templates/mc_exam.template -log -i src/war_unit.yml -q random -f build/Unit1/q_order.txt
	python exam_builder.py src/exam_1.yml -o build/Unit1/AnswerKey.md -t templates/mc_key.template -log -i src/war_unit.yml -q build/Unit1/q_order.txt
	pandoc -H templates/format.sty -o out/Unit1/Exam.pdf build/Unit1/Exam.md
	pandoc -H templates/format.sty -o out/Unit1/AnswerKey.pdf build/Unit1/AnswerKey.md

install:
	install -D exam_builder.py /usr/local/bin/exam_builder


uninstall:
	-rm /usr/local/bin/exam_builder

