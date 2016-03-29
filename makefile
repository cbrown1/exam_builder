example:
	$(eval unit=Unit1)
	mkdir -p build/$(unit)
	mkdir -p out/$(unit)
	python exam_builder3.py -y src/exam_2.yml -o build/$(unit)/test.md -t templates/mc_exam.template
	pandoc -H templates/format.sty -o out/$(unit)/exam_2.pdf build/$(unit)/test.md

install:
	install -D exam_builder.py /usr/local/bin/exam_builder


uninstall:
	-rm /usr/local/bin/exam_builder

