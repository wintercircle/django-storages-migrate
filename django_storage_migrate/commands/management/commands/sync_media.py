# -*- coding: utf-8 -*-
import os
import logging
import sys
from optparse import make_option

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.core.management.base import BaseCommand
from django.core.files.storage import FileSystemStorage, DefaultStorage
from django.core.files import File


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate media files from local media dir into storage (used only with django-storages)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--remove', '-r',
            help='Remove local files after migrate',
            dest='remove',
            action='store_true',
            default=False,
        )

        parser.add_argument(
            '--pk',
            help='Limit to these ids',
            dest='ids',
            action='append',
            default=[],
            type=int
        )

        parser.add_argument(
            '--field', '-f',
            dest='field'
        )

        parser.add_argument(
            '--skip-save', '-s',
            action='store_false',
            dest='save',
            default=True
        )

        parser.add_argument(
            '--model', '-m',
            dest='model'
        )

        parser.add_argument(
            'app',
        )

    def handle(self, *args, **options):

        if not options.get('model') or not options.get('field'):
            raise Exception('Specify model and field options')

        model = apps.get_model(options.get('app'), options.get('model').capitalize())
        field = options.get('field')
        with transaction.atomic():
            query_params = {'%s__gte' % field: 0}
            objects = model.objects.filter(**query_params)
            ids = options.get('ids')
            if len(ids) != 0:
                objects = objects.filter(pk__in=ids)
            for instance in objects:
                file_obj = getattr(instance, field)

                if 'storages.backends' not in settings.DEFAULT_FILE_STORAGE \
                        and isinstance(file_obj.storage, DefaultStorage):
                    raise Exception('Field storage must be not Default')
                file_path = FileSystemStorage().path(file_obj.name)

                if os.path.exists(file_path):
                    _file = File(open(file_path, 'rb'))
                    if hasattr(file_obj.instance, 'add_metadata'):
                        file_obj.instance.add_metadata()
                    file_obj.save(os.path.basename(file_path), _file, save=options.get('save'))

                    if options.get('remove'):
                        os.unlink(file_path)

                    logger.info('File %s for object %s(id=%s, model=%s) successfully uploaded into S3 storage - %s',
                                file_path, instance, instance.pk, model.__name__, file_obj.url)

                else:
                    logger.warning('File %s for object %s(id=%s, model=%s) doesn\'t exists',
                                   file_path, instance, instance.pk, model.__name__)
