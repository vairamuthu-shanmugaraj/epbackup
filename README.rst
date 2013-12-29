This is a simple script to backup a database and a set of files into a single
archive, encrypt it and store it on S3.

The script looks for a "backup.yml" file in the current working directory
which has following structure::

    encryption:
        method: aes
        password: <password>
    database_env: DJANGO_DATABASE_URL
    output_prefix: ep14-%Y%m%d.%H%M%S
    files:
        media: /path/to/djep/site_media
    aws:
        access_key_id: <aws_key>
        access_key_secret: <aws_secret>
        bucket: <bucket_name>

If you want to use GnuPG for encrypting the backup file, set the encryption
method to "gpg" and provide a recipient email address through the encryption
block's "recipient" field.
