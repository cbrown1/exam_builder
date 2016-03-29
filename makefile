example:
	$(eval unit=Unit1)
	mkdir -p build
	mkdir -p out/$(unit)
	python exam_builder3.py src/exam_2.yml build
	for file in build/doc/$(unit)_Exam_*.md; do fname=$${file##*/}; pandoc -H templates/format.sty -o out/$(unit)/$$fname.pdf build/doc/$$fname; done


install:
	install -D exam_builder.py /usr/local/bin/exam_builder


uninstall:
	-rm /usr/local/bin/exam_builder

