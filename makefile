# Python-Markdown makefile

.PHONY : help
help:
	@echo 'Usage: make <subcommand>'
	@echo ''
	@echo 'Subcommands:'
	@echo '    install       Install OpenSimula locally in source mode'
	@echo '    deploy        Register and upload a new release to PyPI'
	@echo '    build         Build a source distribution'
	@echo '    docs          Build documentation'
	@echo '    test          Run all tests'
	@echo '    clean         Clean up the source directories'

.PHONY : install
install:
	pip install -e .

.PHONY : deploy
deploy:
	rm -rf build
	rm -rf dist
	python -m build
	twine upload dist/*

.PHONY : build
build:
	rm -rf build
	rm -rf dist
	python -m build

.PHONY : docs
docs:
	mkdocs build --clean

.PHONY : test
test:
	pytest test

.PHONY : clean
clean:
	rm -rf build
	rm -rf dist
	rm -rf site
