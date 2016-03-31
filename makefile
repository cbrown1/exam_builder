example:
	mkdir -p build/Unit1
	mkdir -p out/Unit1
	python exam_builder.py -y src/exam_1.yml -o build/Unit1/test.md -t templates/mc_exam.template -log -i src/war_unit.yml -f build/q_order.txt
	pandoc -H templates/format.sty -o out/Unit1/exam_1.pdf build/Unit1/test.md

install:
	install -D exam_builder.py /usr/local/bin/exam_builder


uninstall:
	-rm /usr/local/bin/exam_builder

