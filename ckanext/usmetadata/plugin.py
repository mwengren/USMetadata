from logging import getLogger

from ckan.plugins import implements, SingletonPlugin, toolkit, IConfigurer, ITemplateHelpers, IDatasetForm

log = getLogger(__name__)

def _create_access_level_vocabulary():
    '''Create accessLevels vocab and tags, if they don't exist already.'''
    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}

    log.debug("Creating vocab 'public_access_levels'")
    data = {'name': 'public_access_level'}
    vocab = toolkit.get_action('vocabulary_create')(context, data)
    log.debug('Vocab created: %s' % vocab)
    for tag in (u'public', u'restricted'):
        log.debug(
            "Adding tag {0} to vocab 'public_access_levels'".format(tag))
        data = {'name': tag, 'vocabulary_id': vocab['id']}
        toolkit.get_action('tag_create')(context, data)
    return vocab

def get_access_levels():
    log.debug('get_access_levels() called')

    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}

    vocab = None
    try:
        data = {'id': 'public_access_level'} #we can use the id or name for id param
        vocab = toolkit.get_action('vocabulary_show')(context, data)
    except:
        log.debug("vocabulary_show failed, meaning the vocabulary for access level doesn't exist")
        vocab = _create_access_level_vocabulary()

    access_levels = [x['display_name'] for x in vocab['tags']]
    log.debug("vocab tags: %s" % access_levels)

    return access_levels

#excluded title, description, tags and last update as they're part of the default ckan dataset metadata
required_metadata = ['public_access_level', 'publisher', 'contact_name', 'contact_email', 'unique_id']

#excluded download_url, endpoint, format and license as they may be discoverable
required_if_applicable_metadata = ['data_dictionary', 'endpoint', 'spatial', 'temporal']

#some of these could be excluded (e.g. related_documents) which can be captured from other ckan default data
expanded_metadata = ['release_date', 'frequency', 'language', 'granularity', 'data_quality', 'category',
                     'related_documents', 'size', 'homepage_url', 'rss_feed', 'system_of_records',
                     'system_of_records_none_related_to_this_dataset']

class CommonCoreMetadataForm(SingletonPlugin, toolkit.DefaultDatasetForm):
    '''This plugin adds fields for the metadata (known as the Common Core) defined at
    https://github.com/project-open-data/project-open-data.github.io/blob/master/schema.md
    '''

    implements(ITemplateHelpers, inherit=False)
    implements(IConfigurer, inherit=False)
    implements(IDatasetForm, inherit=False)

    def is_fallback(self):
        # Return True so that we use the extension's dataset form instead of CKAN's default for
        # /dataset/new and /dataset/edit
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        #
        return ['dataset', 'package']

    def update_config(self, config):
        # Instruct CKAN to look in the ```templates``` directory for customized templates and snippets
        toolkit.add_template_directory(config, 'templates')

    def _modify_package_schema(self, schema):
        log.debug("_modify_package_schema called")
        #TODO change ignore_missing to not_empty
        for metadata in required_metadata:
            schema.update({
                metadata: [toolkit.get_validator('ignore_missing'),
                           toolkit.get_converter('convert_to_extras')]
            })

        return schema

    def create_package_schema(self):
        log.debug("create_package_schema called")
        schema = super(CommonCoreMetadataForm, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def update_package_schema(self):
        log.debug("update_package_schema called")
        schema = super(CommonCoreMetadataForm, self).update_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    def show_package_schema(self):
        log.debug("show_package_schema called")
        schema = super(CommonCoreMetadataForm, self).show_package_schema()

        # Don't show vocab tags mixed in with normal 'free' tags
        # (e.g. on dataset pages, or on the search page)
        schema['tags']['__extras'].append(toolkit.get_converter('free_tags_only'))
        schema = self._modify_package_schema(schema)
        return schema

    #Method below allows functions and other methods to be called from the Jinja template using the h variable
    def get_helpers(self):
        log.debug('get_helpers() called, getting the access levels')
        return {'public_access_levels': get_access_levels}