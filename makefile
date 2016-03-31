example:
	$(eval unit=Unit1)
	mkdir -p build/$(unit)
	mkdir -p out/$(unit)
	python exam_builder.py -y src/exam_2.yml -o build/$(unit)/test.md -t templates/mc_exam.template -q src/q_order.txt -log
	pandoc -H templates/format.sty -o out/$(unit)/exam_2.pdf build/$(unit)/test.md

install:
	install -D exam_builder.py /usr/local/bin/exam_builder


uninstall:
	-rm /usr/local/bin/exam_builder

