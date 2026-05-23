# Retrieval Eval Misses

## Record 12 pallets__flask-4045 pallets/flask
query: `Blueprint.*"foo\.bar\.baz"`
candidate_hit: `True` candidate_count: `63`
targets:
- `tests/test_basic.py` line=1 kind=Read
top hits:
- score=1.000 `tests/test_blueprints.py:137-138` symbol=`foo` kind=function parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.778 `tests/test_blueprints.py:133-150` symbol=`test_blueprint_url_defaults` kind=function parts={'bm25': 0.9730173573138784, 'ctags': 0.4166666666666667}
- score=0.628 `tests/test_blueprints.py:351-352` symbol=`foo_bar_foo` kind=function parts={'bm25': 0.517908549790769, 'ctags': 0.8333333333333334}
- score=0.628 `tests/test_blueprints.py:310-311` symbol=`foo_bar_foo` kind=function parts={'bm25': 0.517908549790769, 'ctags': 0.8333333333333334}
- score=0.617 `tests/test_blueprints.py:306-307` symbol=`foo_bar` kind=function parts={'bm25': 0.5004484622503819, 'ctags': 0.8333333333333334}

## Record 16 pallets__flask-4045 pallets/flask
query: `dot`
candidate_hit: `True` candidate_count: `21`
targets:
- `tests/test_blueprints.py` line=256 kind=Read
- `tests/test_blueprints.py` line=343 kind=Read
top hits:
- score=0.650 `TASK.md:1-46` symbol=`TASK.md` kind=code parts={'bm25': 1.0, 'ctags': 0.0}
- score=0.510 `docs/blueprints.rst:241-302` symbol=`blueprints.rst` kind=code parts={'bm25': 0.7841395874326205, 'ctags': 0.0}
- score=0.451 `docs/patterns/lazyloading.rst:81-109` symbol=`lazyloading.rst` kind=code parts={'bm25': 0.6941849025385457, 'ctags': 0.0}
- score=0.350 `src/flask/helpers.py:50-62` symbol=`get_load_dotenv` kind=function parts={'bm25': 0.0, 'ctags': 1.0}
- score=0.350 `src/flask/cli.py:25-25` symbol=`dotenv` kind=assignment parts={'bm25': 0.0, 'ctags': 1.0}

## Record 20 pallets__flask-4045 pallets/flask
query: `\..*endpoint\|dot`
candidate_hit: `True` candidate_count: `36`
targets:
- `tests/test_blueprints.py` line=343 kind=Read
top hits:
- score=0.912 `src/flask/helpers.py:287-287` symbol=`endpoint` kind=assignment parts={'bm25': 1.0, 'ctags': 0.75}
- score=0.905 `src/flask/scaffold.py:432-432` symbol=`endpoint` kind=assignment parts={'bm25': 0.9879488688361073, 'ctags': 0.75}
- score=0.901 `src/flask/helpers.py:285-285` symbol=`endpoint` kind=assignment parts={'bm25': 0.9820234584739039, 'ctags': 0.75}
- score=0.883 `src/flask/scaffold.py:506-527` symbol=`endpoint` kind=function parts={'bm25': 0.954875789918637, 'ctags': 0.75}
- score=0.882 `src/flask/app.py:1042-1042` symbol=`endpoint` kind=assignment parts={'bm25': 0.9533547621645055, 'ctags': 0.75}

## Record 22 pallets__flask-4045 pallets/flask
query: `src/flask`
candidate_hit: `True` candidate_count: `80`
targets:
- `src/flask/scaffold.py` line=1 kind=Read
top hits:
- score=0.886 `src/flask/debughelpers.py:128-128` symbol=`src_info` kind=assignment parts={'bm25': 1.0, 'ctags': 0.673913043478261}
- score=0.851 `src/flask/debughelpers.py:124-124` symbol=`src_info` kind=assignment parts={'bm25': 0.9468164392979166, 'ctags': 0.673913043478261}
- score=0.839 `src/flask/debughelpers.py:126-126` symbol=`src_info` kind=assignment parts={'bm25': 0.9273811134596678, 'ctags': 0.673913043478261}
- score=0.716 `src/flask/testing.py:109-109` symbol=`application` kind=assignment parts={'bm25': 0.9149452266508984, 'ctags': 0.3478260869565218}
- score=0.664 `src/flask/helpers.py:42-42` symbol=`val` kind=assignment parts={'bm25': 0.8345759360325755, 'ctags': 0.3478260869565218}

## Record 29 pallets__flask-4045 pallets/flask
query: `src/flask/*.py`
candidate_hit: `True` candidate_count: `80`
targets:
- `src/flask/blueprints.py` line=1 kind=Read
top hits:
- score=0.899 `src/flask/debughelpers.py:128-128` symbol=`src_info` kind=assignment parts={'bm25': 1.0, 'ctags': 0.7115384615384616}
- score=0.858 `src/flask/debughelpers.py:124-124` symbol=`src_info` kind=assignment parts={'bm25': 0.9363566193760469, 'ctags': 0.7115384615384616}
- score=0.843 `src/flask/debughelpers.py:126-126` symbol=`src_info` kind=assignment parts={'bm25': 0.9135758428101547, 'ctags': 0.7115384615384616}
- score=0.757 `src/flask/testing.py:109-109` symbol=`application` kind=assignment parts={'bm25': 0.9369525852792479, 'ctags': 0.4230769230769232}
- score=0.748 `src/flask/__main__.py:1-3` symbol=`__main__.py` kind=code parts={'bm25': 0.7673208610957167, 'ctags': 0.7115384615384616}

## Record 30 pallets__flask-4045 pallets/flask
query: `dot`
candidate_hit: `True` candidate_count: `21`
targets:
- `tests/test_blueprints.py` line=1 kind=Read
top hits:
- score=0.650 `TASK.md:1-46` symbol=`TASK.md` kind=code parts={'bm25': 1.0, 'ctags': 0.0}
- score=0.510 `docs/blueprints.rst:241-302` symbol=`blueprints.rst` kind=code parts={'bm25': 0.7841373416088369, 'ctags': 0.0}
- score=0.451 `docs/patterns/lazyloading.rst:81-109` symbol=`lazyloading.rst` kind=code parts={'bm25': 0.6941848671665898, 'ctags': 0.0}
- score=0.350 `src/flask/helpers.py:50-62` symbol=`get_load_dotenv` kind=function parts={'bm25': 0.0, 'ctags': 1.0}
- score=0.350 `src/flask/cli.py:25-25` symbol=`dotenv` kind=assignment parts={'bm25': 0.0, 'ctags': 1.0}

## Record 34 pallets__flask-4045 pallets/flask
query: `ValueError.*dot\|dot.*ValueError`
candidate_hit: `False` candidate_count: `26`
targets:
- `verify_fix.py` line=None kind=Write
top hits:
- score=0.650 `TASK.md:1-46` symbol=`TASK.md` kind=code parts={'bm25': 1.0, 'ctags': 0.0}
- score=0.542 `tests/test_helpers.py:309-313` symbol=`test_open_resource_exceptions` kind=function parts={'bm25': 0.8335629989627733, 'ctags': 0.0}
- score=0.516 `src/flask/blueprints.py:357-373` symbol=`add_url_rule` kind=function parts={'bm25': 0.7943092032029128, 'ctags': 0.0}
- score=0.485 `tests/test_helpers.py:120-125` symbol=`test_url_for_with_scheme_not_external` kind=function parts={'bm25': 0.7455814155181313, 'ctags': 0.0}
- score=0.478 `src/flask/scaffold.py:771-820` symbol=`_find_package_path` kind=function parts={'bm25': 0.7355715884184648, 'ctags': 0.0}

## Record 39 django__django-10924 django/django
query: `class FileField`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/db/models/fields/files.py` line=212 kind=Read
top hits:
- score=0.881 `tests/admin_widgets/models.py:7-8` symbol=`MyFileField` kind=type parts={'bm25': 1.0, 'ctags': 0.6590909090909091}
- score=0.788 `tests/invalid_models_tests/test_ordinary_fields.py:525-576` symbol=`FileFieldTests` kind=type parts={'bm25': 0.8567817528029399, 'ctags': 0.6590909090909091}
- score=0.768 `tests/model_forms/models.py:135-139` symbol=`CustomFileField` kind=type parts={'bm25': 0.8273553960230088, 'ctags': 0.6590909090909091}
- score=0.729 `tests/forms_tests/tests/test_forms.py:2472-2478` symbol=`test_filefield_initial_callable` kind=function parts={'bm25': 0.8884705584021457, 'ctags': 0.43181818181818177}
- score=0.709 `tests/forms_tests/field_tests/test_filefield.py:8-82` symbol=`FileFieldTest` kind=type parts={'bm25': 0.6628049455380578, 'ctags': 0.7954545454545453}

## Record 40 django__django-10924 django/django
query: `FunctionType\|callable`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/db/migrations/serializer.py` line=135 kind=Read
- `tests/forms_tests/field_tests/test_filepathfield.py` line=1 kind=Read
top hits:
- score=0.979 `tests/transactions/tests.py:406-408` symbol=`Callable` kind=type parts={'bm25': 0.9671645819796015, 'ctags': 1.0}
- score=0.960 `tests/invalid_models_tests/test_ordinary_fields.py:569-570` symbol=`callable` kind=function parts={'bm25': 0.937783594844577, 'ctags': 1.0}
- score=0.952 `tests/dispatch/tests.py:32-37` symbol=`Callable` kind=type parts={'bm25': 0.9257190212174617, 'ctags': 1.0}
- score=0.918 `django/contrib/admin/options.py:868-868` symbol=`callable` kind=assignment parts={'bm25': 0.9758922548840013, 'ctags': 0.8095238095238094}
- score=0.863 `tests/transactions/tests.py:403-411` symbol=`test_wrap_callable_instance` kind=function parts={'bm25': 0.9822445000422315, 'ctags': 0.6428571428571428}

## Record 42 django__django-10924 django/django
query: `self\.path`
candidate_hit: `False` candidate_count: `80`
targets:
- `django/forms/fields.py` line=1078 kind=Read
- `django/forms/fields.py` line=None kind=Read
top hits:
- score=1.000 `tests/staticfiles_tests/storage.py:40-40` symbol=`path` kind=assignment parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.981 `tests/model_forms/models.py:157-157` symbol=`path` kind=assignment parts={'bm25': 0.9702466346400975, 'ctags': 1.0}
- score=0.981 `tests/model_forms/models.py:175-175` symbol=`path` kind=assignment parts={'bm25': 0.9702466346400975, 'ctags': 1.0}
- score=0.940 `tests/staticfiles_tests/storage.py:56-57` symbol=`path` kind=function parts={'bm25': 0.908223873777766, 'ctags': 1.0}
- score=0.865 `tests/file_storage/tests.py:277-291` symbol=`test_file_save_with_path` kind=function parts={'bm25': 0.9763550154931951, 'ctags': 0.6590909090909091}

## Record 47 django__django-10914 django/django
query: `class.*Permission`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/conf/global_settings.py` line=None kind=Edit
- `tests/test_utils/tests.py` line=1090 kind=Read
- `tests/test_utils/tests.py` line=1096 kind=Read
top hits:
- score=0.835 `tests/admin_views/custom_has_permission_admin.py:20-27` symbol=`HasPermissionAdmin` kind=type parts={'bm25': 0.8555955004130522, 'ctags': 0.7954545454545453}
- score=0.834 `tests/auth_tests/test_checks.py:120-202` symbol=`ModelsPermissionsChecksTests` kind=type parts={'bm25': 0.9276418064469868, 'ctags': 0.6590909090909091}
- score=0.828 `tests/admin_views/custom_has_permission_admin.py:13-17` symbol=`PermissionAdminAuthenticationForm` kind=type parts={'bm25': 0.845905958650258, 'ctags': 0.7954545454545453}
- score=0.812 `django/contrib/auth/mixins.py:55-85` symbol=`PermissionRequiredMixin` kind=type parts={'bm25': 0.8940563904438257, 'ctags': 0.6590909090909091}
- score=0.806 `django/contrib/auth/models.py:33-78` symbol=`Permission` kind=type parts={'bm25': 0.7014198537041285, 'ctags': 1.0}

## Record 61 django__django-10914 django/django
query: `__pycache__`
candidate_hit: `False` candidate_count: `4`
targets:
- `tests/runtests.py` line=1 kind=Read
- `tests/test_utils/tests.py` line=None kind=Edit
top hits:
- score=0.650 `tests/i18n/utils.py:9-10` symbol=`copytree` kind=function parts={'bm25': 1.0, 'ctags': 0.0}
- score=0.333 `django/forms/fields.py:1078-1119` symbol=`FilePathField` kind=type parts={'bm25': 0.5123217122074325, 'ctags': 0.0}
- score=0.332 `tests/i18n/test_extraction.py:663-673` symbol=`test_all_locales` kind=function parts={'bm25': 0.5100027805414508, 'ctags': 0.0}
- score=0.325 `django/forms/fields.py:1079-1119` symbol=`__init__` kind=function parts={'bm25': 0.5000741465020873, 'ctags': 0.0}
- score=0.229 `tests/i18n/test_extraction.py:652-673` symbol=`MultipleLocaleExtractionTests` kind=type parts={'bm25': 0.35260228614265116, 'ctags': 0.0}

## Record 68 django__django-10924 django/django
query: `class FileField`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/db/models/fields/files.py` line=1 kind=Read
top hits:
- score=0.881 `tests/admin_widgets/models.py:7-8` symbol=`MyFileField` kind=type parts={'bm25': 1.0, 'ctags': 0.6590909090909091}
- score=0.797 `tests/invalid_models_tests/test_ordinary_fields.py:525-576` symbol=`FileFieldTests` kind=type parts={'bm25': 0.8719498788588329, 'ctags': 0.6590909090909091}
- score=0.775 `tests/model_forms/models.py:135-139` symbol=`CustomFileField` kind=type parts={'bm25': 0.8376062906626124, 'ctags': 0.6590909090909091}
- score=0.733 `tests/forms_tests/tests/test_forms.py:2472-2478` symbol=`test_filefield_initial_callable` kind=function parts={'bm25': 0.8957210822177502, 'ctags': 0.43181818181818177}
- score=0.720 `tests/forms_tests/field_tests/test_filefield.py:8-82` symbol=`FileFieldTest` kind=type parts={'bm25': 0.6788053693985624, 'ctags': 0.7954545454545453}

## Record 69 django__django-10924 django/django
query: `upload_to`
candidate_hit: `False` candidate_count: `80`
targets:
- `django/db/models/fields/files.py` line=265 kind=Read
top hits:
- score=0.972 `tests/file_uploads/tests.py:23-23` symbol=`UPLOAD_TO` kind=assignment parts={'bm25': 0.9566419049347513, 'ctags': 1.0}
- score=0.964 `tests/file_storage/test_generate_filename.py:48-49` symbol=`upload_to` kind=function parts={'bm25': 0.943963210543388, 'ctags': 1.0}
- score=0.951 `tests/file_storage/test_generate_filename.py:79-81` symbol=`upload_to` kind=function parts={'bm25': 0.9238993683819564, 'ctags': 1.0}
- score=0.866 `tests/file_storage/test_generate_filename.py:47-55` symbol=`test_filefield_generate_filename_with_upload_to` kind=function parts={'bm25': 0.8833589160363617, 'ctags': 0.8333333333333334}
- score=0.767 `tests/file_storage/test_generate_filename.py:51-51` symbol=`f` kind=assignment parts={'bm25': 1.0, 'ctags': 0.3333333333333333}

## Record 75 django__django-10924 django/django
query: `callable\|function`
candidate_hit: `False` candidate_count: `80`
targets:
- `django/db/migrations/serializer.py` line=140 kind=Read
- `django/forms/fields.py` line=None kind=Edit
- `django/db/models/fields/__init__.py` line=1688 kind=Read
- `django/db/models/fields/__init__.py` line=None kind=Edit
top hits:
- score=0.845 `tests/template_tests/test_callables.py:13-40` symbol=`test_callable` kind=function parts={'bm25': 0.8564903143979767, 'ctags': 0.8250000000000002}
- score=0.720 `django/utils/functional.py:347-357` symbol=`__init__` kind=function parts={'bm25': 1.0, 'ctags': 0.2}
- score=0.718 `django/contrib/gis/db/models/functions.py:266-266` symbol=`function` kind=assignment parts={'bm25': 0.5658678455061376, 'ctags': 1.0}
- score=0.718 `django/contrib/gis/db/models/functions.py:262-262` symbol=`function` kind=assignment parts={'bm25': 0.5658678455061376, 'ctags': 1.0}
- score=0.718 `django/contrib/gis/db/models/functions.py:342-342` symbol=`function` kind=assignment parts={'bm25': 0.5658678455061376, 'ctags': 1.0}

## Record 76 django__django-10924 django/django
query: `def test_file_path_field`
candidate_hit: `False` candidate_count: `80`
targets:
- `test_filepathfield_migration.py` line=None kind=Write
- `test_callable_basic.py` line=None kind=Write
- `verify_filepathfield_callable.py` line=None kind=Write
top hits:
- score=1.000 `tests/field_deconstruction/tests.py:177-187` symbol=`test_file_path_field` kind=function parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.523 `tests/forms_tests/field_tests/test_filepathfield.py:6-6` symbol=`PATH` kind=assignment parts={'bm25': 0.557173711914924, 'ctags': 0.45999999999999996}
- score=0.494 `django/db/models/fields/files.py:55-57` symbol=`path` kind=function parts={'bm25': 0.4914908326369648, 'ctags': 0.5}
- score=0.479 `tests/forms_tests/field_tests/test_imagefield.py:18-19` symbol=`get_img_path` kind=function parts={'bm25': 0.547991016323427, 'ctags': 0.35}
- score=0.474 `tests/field_deconstruction/tests.py:164-175` symbol=`test_file_field` kind=function parts={'bm25': 0.5410601603726993, 'ctags': 0.35}

## Record 81 django__django-11039 django/django
query: `atomic_migration = self.connection.features.can_rollback_ddl`
candidate_hit: `True` candidate_count: `80`
targets:
- `tests/migrations/test_commands.py` line=1 kind=Read
top hits:
- score=1.000 `django/db/backends/base/schema.py:97-97` symbol=`atomic_migration` kind=assignment parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.650 `django/db/backends/base/features.py:167-167` symbol=`can_rollback_ddl` kind=assignment parts={'bm25': 0.5981254560656173, 'ctags': 0.7467532467532467}
- score=0.650 `django/db/backends/postgresql/features.py:28-28` symbol=`can_rollback_ddl` kind=assignment parts={'bm25': 0.5981254560656173, 'ctags': 0.7467532467532467}
- score=0.650 `django/db/backends/sqlite3/features.py:24-24` symbol=`can_rollback_ddl` kind=assignment parts={'bm25': 0.5981254560656173, 'ctags': 0.7467532467532467}
- score=0.508 `django/db/backends/base/schema.py:92-97` symbol=`__init__` kind=function parts={'bm25': 0.6980250005473031, 'ctags': 0.15584415584415584}

## Record 83 django__django-11039 django/django
query: `non_atomic`
candidate_hit: `True` candidate_count: `80`
targets:
- `tests/migrations/test_commands.py` line=524 kind=Read
- `tests/migrations/test_migrations_non_atomic/0001_initial.py` line=1 kind=Read
- `tests/migrations/test_migrations/0001_initial.py` line=1 kind=Read
top hits:
- score=1.000 `django/core/handlers/base.py:65-65` symbol=`non_atomic_requests` kind=assignment parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.987 `django/db/transaction.py:295-300` symbol=`_non_atomic_requests` kind=function parts={'bm25': 0.9796280992321347, 'ctags': 1.0}
- score=0.970 `django/db/transaction.py:299-299` symbol=`_non_atomic_requests` kind=assignment parts={'bm25': 0.9532166219148207, 'ctags': 1.0}
- score=0.967 `django/db/transaction.py:303-309` symbol=`non_atomic_requests` kind=function parts={'bm25': 0.9495216525041653, 'ctags': 1.0}
- score=0.952 `tests/migrations/test_operations.py:2425-2425` symbol=`non_atomic_migration` kind=assignment parts={'bm25': 0.9259927927719036, 'ctags': 1.0}

## Record 87 django__django-11039 django/django
query: `^class`
candidate_hit: `False` candidate_count: `80`
targets:
- `django/core/management/commands/sqlmigrate.py` line=55 kind=Read
- `django/core/management/commands/sqlmigrate.py` line=None kind=Edit
- `django/core/management/commands/sqlmigrate.py` line=1 kind=Read
- `django/core/management/commands/sqlmigrate.py` line=56 kind=Read
top hits:
- score=1.000 `tests/select_related_regress/models.py:64-65` symbol=`Class` kind=type parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.931 `tests/utils_tests/test_functional.py:109-120` symbol=`Class` kind=type parts={'bm25': 0.8936464228942405, 'ctags': 1.0}
- score=0.924 `tests/utils_tests/test_functional.py:83-98` symbol=`Class` kind=type parts={'bm25': 0.8828873250728572, 'ctags': 1.0}
- score=0.848 `docs/ref/models/class.txt:1-35` symbol=`class.txt` kind=code parts={'bm25': 0.9088730040657005, 'ctags': 0.7352941176470589}
- score=0.839 `tests/utils_tests/test_functional.py:56-57` symbol=`SubClass` kind=type parts={'bm25': 0.990387790530306, 'ctags': 0.5588235294117647}

## Record 88 django__django-11001 django/django
query: `compiler`
candidate_hit: `True` candidate_count: `65`
targets:
- `django/db/models/sql/compiler.py` line=1 kind=Read
top hits:
- score=1.000 `django/contrib/admin/bin/compress.py:31-31` symbol=`compiler` kind=assignment parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.984 `django/db/models/query.py:103-103` symbol=`compiler` kind=assignment parts={'bm25': 0.975149565679188, 'ctags': 1.0}
- score=0.984 `django/db/models/query.py:125-125` symbol=`compiler` kind=assignment parts={'bm25': 0.975149565679188, 'ctags': 1.0}
- score=0.982 `django/db/models/sql/query.py:537-537` symbol=`compiler` kind=assignment parts={'bm25': 0.9726076940372294, 'ctags': 1.0}
- score=0.982 `django/db/models/sql/query.py:529-529` symbol=`compiler` kind=assignment parts={'bm25': 0.9726076940372294, 'ctags': 1.0}

## Record 94 django__django-11001 django/django
query: `class OrderingTests`
candidate_hit: `True` candidate_count: `80`
targets:
- `tests/queries/tests.py` line=2020 kind=Read
top hits:
- score=1.000 `tests/select_related_regress/models.py:64-65` symbol=`Class` kind=type parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.931 `tests/utils_tests/test_functional.py:109-120` symbol=`Class` kind=type parts={'bm25': 0.894552837078991, 'ctags': 1.0}
- score=0.925 `tests/utils_tests/test_functional.py:83-98` symbol=`Class` kind=type parts={'bm25': 0.8838737503615003, 'ctags': 1.0}
- score=0.849 `docs/ref/models/class.txt:1-35` symbol=`class.txt` kind=code parts={'bm25': 0.9100093158151341, 'ctags': 0.7352941176470589}
- score=0.839 `tests/utils_tests/test_functional.py:56-57` symbol=`SubClass` kind=type parts={'bm25': 0.9903119672380408, 'ctags': 0.5588235294117647}

## Record 95 django__django-11001 django/django
query: `def test_order_by_extra`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/db/models/sql/compiler.py` line=35 kind=Read
- `django/db/models/sql/compiler.py` line=351 kind=Read
- `django/db/models/sql/compiler.py` line=364 kind=Read
top hits:
- score=1.000 `tests/queries/tests.py:2031-2032` symbol=`test_order_by_extra` kind=function parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.544 `tests/queries/tests.py:2280-2286` symbol=`test_extra_multiple_select_params_values_order_by` kind=function parts={'bm25': 0.47906023210208204, 'ctags': 0.6638655462184874}
- score=0.501 `django/db/models/sql/query.py:639-639` symbol=`extra_order_by` kind=assignment parts={'bm25': 0.45793523666649827, 'ctags': 0.5798319327731093}
- score=0.489 `django/db/models/sql/query.py:1933-1933` symbol=`extra_order_by` kind=assignment parts={'bm25': 0.4398589084303619, 'ctags': 0.5798319327731093}
- score=0.487 `tests/ordering/tests.py:254-267` symbol=`test_extra_ordering_quoting` kind=function parts={'bm25': 0.4779285292773442, 'ctags': 0.5042016806722689}

## Record 96 django__django-11001 django/django
query: `status`
candidate_hit: `False` candidate_count: `80`
targets:
- `tests/queries/models.py` line=600 kind=Read
- `django/db/models/sql/compiler.py` line=None kind=Edit
- `django/db/models/sql/compiler.py` line=351 kind=Read
top hits:
- score=1.000 `tests/handlers/tests.py:184-184` symbol=`status` kind=assignment parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.992 `tests/logging_tests/views.py:35-35` symbol=`status` kind=assignment parts={'bm25': 0.988190806385483, 'ctags': 1.0}
- score=0.974 `tests/model_forms/models.py:54-54` symbol=`status` kind=assignment parts={'bm25': 0.9598271181644555, 'ctags': 1.0}
- score=0.969 `tests/select_for_update/tests.py:151-151` symbol=`status` kind=assignment parts={'bm25': 0.95189539456826, 'ctags': 1.0}
- score=0.969 `tests/select_for_update/tests.py:415-415` symbol=`status` kind=assignment parts={'bm25': 0.95189539456826, 'ctags': 1.0}

## Record 99 django__django-11001 django/django
query: `RawSQL`
candidate_hit: `True` candidate_count: `15`
targets:
- `tests/queries/tests.py` line=3920 kind=Read
- `tests/queries/tests.py` line=1 kind=Read
- `tests/queries/tests.py` line=None kind=Edit
- `tests/queries/tests.py` line=3925 kind=Read
top hits:
- score=0.908 `django/db/models/expressions.py:676-690` symbol=`RawSQL` kind=type parts={'bm25': 0.858407896747392, 'ctags': 1.0}
- score=0.796 `tests/annotations/tests.py:327-335` symbol=`test_rawsql_group_by_collapse` kind=function parts={'bm25': 0.9551810678380732, 'ctags': 0.5}
- score=0.650 `tests/expressions/tests.py:74-74` symbol=`companies` kind=assignment parts={'bm25': 1.0, 'ctags': 0.0}
- score=0.643 `tests/annotations/tests.py:328-328` symbol=`raw` kind=assignment parts={'bm25': 0.9886216185404233, 'ctags': 0.0}
- score=0.618 `tests/db_functions/comparison/test_least.py:56-56` symbol=`future_sql` kind=assignment parts={'bm25': 0.9506551590289849, 'ctags': 0.0}

## Record 100 astropy__astropy-12907 astropy/astropy
query: `Test 1`
candidate_hit: `False` candidate_count: `80`
targets:
- `test_nested_compound.py` line=None kind=Write
- `astropy/modeling/separable.py` line=219 kind=Read
top hits:
- score=0.984 `astropy/extern/jquery/data/js/jquery-3.1.1.js:1361-1440` symbol=`jquery-3.1.1.js` kind=code parts={'bm25': 0.9747584495054884, 'ctags': 1.0}
- score=0.974 `astropy/extern/jquery/data/js/jquery-3.1.1.js:9601-9680` symbol=`jquery-3.1.1.js` kind=code parts={'bm25': 0.959855862695493, 'ctags': 1.0}
- score=0.956 `astropy/extern/jquery/data/js/jquery-3.1.1.js:5441-5520` symbol=`jquery-3.1.1.js` kind=code parts={'bm25': 0.9330053404246395, 'ctags': 1.0}
- score=0.956 `astropy/extern/jquery/data/js/jquery-3.1.1.js:8401-8480` symbol=`jquery-3.1.1.js` kind=code parts={'bm25': 0.9320589698943567, 'ctags': 1.0}
- score=0.932 `astropy/extern/jquery/data/js/jquery-3.1.1.js:2081-2160` symbol=`jquery-3.1.1.js` kind=code parts={'bm25': 0.894891750529572, 'ctags': 1.0}

## Record 101 django__django-10914 django/django
query: `(settings|upload)`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/conf/global_settings.py` line=1 kind=Read
top hits:
- score=0.927 `tests/requests/test_data_upload_settings.py:94-97` symbol=`test_data_upload_max_memory_size_exceeded` kind=function parts={'bm25': 0.9354487199074435, 'ctags': 0.911764705882353}
- score=0.895 `tests/file_storage/tests.py:522-525` symbol=`settings` kind=assignment parts={'bm25': 0.8388444493227696, 'ctags': 1.0}
- score=0.893 `tests/requests/test_data_upload_settings.py:9-9` symbol=`TOO_MUCH_DATA_MSG` kind=assignment parts={'bm25': 0.9627322580064123, 'ctags': 0.7647058823529412}
- score=0.884 `tests/requests/test_data_upload_settings.py:86-109` symbol=`DataUploadMaxMemorySizeGetTests` kind=type parts={'bm25': 0.869151931638021, 'ctags': 0.911764705882353}
- score=0.875 `tests/requests/test_data_upload_settings.py:8-8` symbol=`TOO_MANY_FIELDS_MSG` kind=assignment parts={'bm25': 0.9337245903294284, 'ctags': 0.7647058823529412}

## Record 109 django__django-10924 django/django
query: `FilePathField`
candidate_hit: `True` candidate_count: `37`
targets:
- `tests/field_deconstruction/tests.py` line=175 kind=Read
top hits:
- score=0.907 `tests/forms_tests/field_tests/test_filepathfield.py:22-99` symbol=`FilePathFieldTest` kind=type parts={'bm25': 1.0, 'ctags': 0.7352941176470589}
- score=0.825 `tests/model_fields/test_promises.py:58-62` symbol=`test_FilePathField` kind=function parts={'bm25': 0.9680048373361289, 'ctags': 0.5588235294117647}
- score=0.750 `tests/forms_tests/field_tests/test_filepathfield.py:52-52` symbol=`f` kind=assignment parts={'bm25': 0.995444100148296, 'ctags': 0.29411764705882354}
- score=0.750 `tests/forms_tests/field_tests/test_filepathfield.py:45-45` symbol=`f` kind=assignment parts={'bm25': 0.995444100148296, 'ctags': 0.29411764705882354}
- score=0.730 `tests/forms_tests/field_tests/test_filepathfield.py:59-59` symbol=`f` kind=assignment parts={'bm25': 0.9642390634712471, 'ctags': 0.29411764705882354}

## Record 111 django__django-10924 django/django
query: `class FileField`
candidate_hit: `True` candidate_count: `80`
targets:
- `django/db/models/fields/files.py` line=212 kind=Read
top hits:
- score=0.881 `tests/admin_widgets/models.py:7-8` symbol=`MyFileField` kind=type parts={'bm25': 1.0, 'ctags': 0.6590909090909091}
- score=0.788 `tests/invalid_models_tests/test_ordinary_fields.py:525-576` symbol=`FileFieldTests` kind=type parts={'bm25': 0.8567862120125381, 'ctags': 0.6590909090909091}
- score=0.768 `tests/model_forms/models.py:135-139` symbol=`CustomFileField` kind=type parts={'bm25': 0.8273584274641556, 'ctags': 0.6590909090909091}
- score=0.729 `tests/forms_tests/tests/test_forms.py:2472-2478` symbol=`test_filefield_initial_callable` kind=function parts={'bm25': 0.8884728177396204, 'ctags': 0.43181818181818177}
- score=0.709 `tests/forms_tests/field_tests/test_filefield.py:8-82` symbol=`FileFieldTest` kind=type parts={'bm25': 0.6628097592232638, 'ctags': 0.7954545454545453}

## Record 115 django__django-11001 django/django
query: `compiler`
candidate_hit: `True` candidate_count: `64`
targets:
- `django/db/models/sql/compiler.py` line=1 kind=Read
top hits:
- score=1.000 `django/contrib/admin/bin/compress.py:31-31` symbol=`compiler` kind=assignment parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.984 `django/db/models/query.py:103-103` symbol=`compiler` kind=assignment parts={'bm25': 0.9748069351098565, 'ctags': 1.0}
- score=0.984 `django/db/models/query.py:125-125` symbol=`compiler` kind=assignment parts={'bm25': 0.9748069351098565, 'ctags': 1.0}
- score=0.982 `django/db/models/sql/query.py:537-537` symbol=`compiler` kind=assignment parts={'bm25': 0.9720601610775503, 'ctags': 1.0}
- score=0.982 `django/db/models/sql/query.py:529-529` symbol=`compiler` kind=assignment parts={'bm25': 0.9720601610775503, 'ctags': 1.0}

## Record 117 django__django-11001 django/django
query: `RawSQL\|order_by\|Order`
candidate_hit: `True` candidate_count: `80`
targets:
- `tests/expressions/tests.py` line=379 kind=Read
- `tests/expressions/models.py` line=1 kind=Read
- `tests/expressions/tests.py` line=1 kind=Read
top hits:
- score=0.952 `django/db/models/sql/query.py:638-638` symbol=`order_by` kind=assignment parts={'bm25': 0.9262846851722002, 'ctags': 1.0}
- score=0.949 `django/db/models/query.py:619-619` symbol=`order_by` kind=assignment parts={'bm25': 0.9216649693306184, 'ctags': 1.0}
- score=0.946 `django/db/models/expressions.py:1149-1149` symbol=`order_by` kind=assignment parts={'bm25': 0.9165432391987155, 'ctags': 1.0}
- score=0.939 `django/db/models/expressions.py:1165-1165` symbol=`order_by` kind=assignment parts={'bm25': 0.9064675271032645, 'ctags': 1.0}
- score=0.927 `django/db/models/sql/compiler.py:51-51` symbol=`order_by` kind=assignment parts={'bm25': 0.8881300262347458, 'ctags': 1.0}

## Record 119 django__django-11001 django/django
query: `^class`
candidate_hit: `False` candidate_count: `80`
targets:
- `tests/expressions/tests.py` line=600 kind=Read
- `tests/expressions/tests.py` line=618 kind=Read
- `tests/expressions/tests.py` line=None kind=Edit
top hits:
- score=1.000 `tests/select_related_regress/models.py:64-65` symbol=`Class` kind=type parts={'bm25': 1.0, 'ctags': 1.0}
- score=0.931 `tests/utils_tests/test_functional.py:109-120` symbol=`Class` kind=type parts={'bm25': 0.8937947765820242, 'ctags': 1.0}
- score=0.924 `tests/utils_tests/test_functional.py:83-98` symbol=`Class` kind=type parts={'bm25': 0.8830489542960644, 'ctags': 1.0}
- score=0.848 `docs/ref/models/class.txt:1-35` symbol=`class.txt` kind=code parts={'bm25': 0.9090530261068835, 'ctags': 0.7352941176470589}
- score=0.839 `tests/utils_tests/test_functional.py:56-57` symbol=`SubClass` kind=type parts={'bm25': 0.9903779694710874, 'ctags': 0.5588235294117647}
