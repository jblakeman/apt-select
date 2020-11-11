all: package

package: package-dependencies
	@fpm-cook package deb-package.rb

package-dependencies:
	@if ! `gem list -i fpm-cookery`; then gem install fpm-cookery; fi
