from pyramid.config import Configurator

def paster_main(global_config, **local_config):
    settings = dict(global_config)
    settings.update(local_config)

    config = Configurator(settings=settings) 
    config.add_route('generate', '/g/{filename_part}.svg')
    config.add_route('fetch', '/f/*repo_url_and_path')
    config.scan('.')

    from .git import GitFetcher
    from .interfaces import IGitFetcher
    config.registry.registerUtility(
        GitFetcher(config.registry.settings['repos_base_dir']),
        IGitFetcher
        )
    return config.make_wsgi_app()
