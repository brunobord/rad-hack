help:
	@echo "Build 'RAD-Hack' HTML files using the following command:"
	@echo ""
	@echo "  make clean: delete the 'build' directory"
	@echo "  make html: build HTML pages."
	@echo ""

clean:
	rm -Rf build/

html:
	tox -e html
