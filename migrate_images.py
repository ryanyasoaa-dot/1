"""
migrate_images.py
-----------------
One-time script: uploads every existing local product image to Supabase Storage
and updates the image_url in the product_images table to the new public URL.

Run once from the project root:
    python migrate_images.py

Safe to re-run — already-migrated rows (URLs starting with 'http') are skipped.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

BUCKET     = 'product-images'
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

client = create_client(SUPABASE_URL, SUPABASE_KEY)


def public_url(storage_path: str) -> str:
    res = client.storage.from_(BUCKET).get_public_url(storage_path)
    return res if isinstance(res, str) else res.get('publicURL', '')


def migrate():
    rows = client.table('product_images').select('id, image_url').execute().data or []
    print(f'Found {len(rows)} image rows.')

    migrated = skipped = failed = 0

    for row in rows:
        url: str = row.get('image_url', '')

        # Already a cloud URL — skip
        if url.startswith('http'):
            skipped += 1
            continue

        # Normalise local path
        local_path = url.lstrip('/')
        if not os.path.isfile(local_path):
            print(f'  [MISSING]  {local_path}')
            failed += 1
            continue

        with open(local_path, 'rb') as f:
            data = f.read()

        ext = local_path.rsplit('.', 1)[-1].lower()
        storage_path = f"migrated/{row['id']}.{ext}"

        try:
            client.storage.from_(BUCKET).upload(
                path=storage_path,
                file=data,
                file_options={'content-type': f'image/{ext}', 'cache-control': '31536000'},
            )
            new_url = public_url(storage_path)
            client.table('product_images').update({'image_url': new_url}).eq('id', row['id']).execute()
            print(f'  [OK]  {local_path}  →  {new_url}')
            migrated += 1
        except Exception as e:
            print(f'  [ERROR]  {local_path}: {e}')
            failed += 1

    print(f'\nDone. Migrated: {migrated}  |  Skipped: {skipped}  |  Failed: {failed}')


if __name__ == '__main__':
    migrate()
