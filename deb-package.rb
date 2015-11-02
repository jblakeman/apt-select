class AptSelect < FPM::Cookery::Recipe
  name        'apt-select'
  version     '0.1.0'
  revision    0
  homepage    'https://github.com/jblakeman/apt-select'
  license     'MIT'
  description 'Choose a fast, up to date Ubuntu apt mirror'
  maintainer  'Gabriel Mazetto <brodock@gmail.com>'
  source      './', :with => :local_path

  platforms [:ubuntu] do
    depends 'python-bs4'
  end

  def build
  end

  def install
    share('apt-select').mkdir
    share('apt-select/bin').mkdir
    Dir["#{workdir}/*"].each { |f| share('apt-select').install f if allowed_file?(f) }
    Dir["#{workdir}/bin/*"].each { |f| share('apt-select/bin').install f }

    with_trueprefix do
      create_post_install_hook <<-EOF
        set -e
        BIN_PATH="#{share('apt-select/bin')}"

        update-alternatives --install /usr/bin/apt-select apt-select $BIN_PATH/apt-select 100
        update-alternatives --install /usr/bin/apt-select-update apt-select-update $BIN_PATH/apt-select-update 100

        exit 0
      EOF
      create_pre_uninstall_hook <<-EOF
        set -e
        BIN_PATH="#{share('apt-select/bin')}"

        if [ "$1" != "upgrade" ]; then
          update-alternatives --remove apt-select $BIN_PATH/apt-select
          update-alternatives --remove apt-select-update $BIN_PATH/apt-select-update
        fi

        exit 0
      EOF
    end
  end

  private

  def allowed_file?(file)
    allowed_formats = %w(.py .md .sh)
    allowed_formats.include? File.extname(file)
  end

  def create_post_install_hook(script, interpreter = '/bin/sh')
    File.open(builddir('post-install'), 'w', 0755) do |f|
      f.write "#!#{interpreter}\n" + script.gsub(/^\s+/, '')
      self.class.post_install(File.expand_path(f.path))
    end
  end

  def create_pre_uninstall_hook(script, interpreter = '/bin/sh')
    File.open(builddir('pre-uninstall'), 'w', 0755) do |f|
      f.write "#!#{interpreter}\n" + script.gsub(/^\s+/, '')
      self.class.pre_uninstall(File.expand_path(f.path))
    end
  end
end
