# Supabase Storage Setup

This guide explains how to set up the required Supabase Storage buckets for the UnFuzz application.

## Required Storage Buckets

### 1. `enhanced-images` Bucket
Stores enhanced/edited images saved to user libraries.

**Setup Steps:**
1. Go to your Supabase project dashboard
2. Navigate to **Storage** in the left sidebar
3. Click **New Bucket**
4. Configure the bucket:
   - **Name:** `enhanced-images`
   - **Public bucket:** ✅ Yes (checked)
   - **File size limit:** 50 MB (recommended)
   - **Allowed MIME types:** `image/jpeg`, `image/jpg`, `image/png`, `image/webp`

5. Click **Create Bucket**

### 2. `team-logos` Bucket
Stores team logo images (should already exist).

**Setup Steps:**
1. Go to your Supabase project dashboard
2. Navigate to **Storage** in the left sidebar
3. Click **New Bucket**
4. Configure the bucket:
   - **Name:** `team-logos`
   - **Public bucket:** ✅ Yes (checked)
   - **File size limit:** 5 MB (recommended)
   - **Allowed MIME types:** `image/jpeg`, `image/jpg`, `image/png`

5. Click **Create Bucket**

## Storage Policies (Row Level Security)

After creating the buckets, you need to set up access policies:

### For `enhanced-images` bucket:

**Policy 1: Allow authenticated users to upload**
```sql
CREATE POLICY "Allow authenticated users to upload enhanced images"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'enhanced-images');
```

**Policy 2: Allow public read access**
```sql
CREATE POLICY "Allow public read access to enhanced images"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'enhanced-images');
```

**Policy 3: Allow users to delete their own images**
```sql
CREATE POLICY "Allow users to delete their own enhanced images"
ON storage.objects
FOR DELETE
TO authenticated
USING (bucket_id = 'enhanced-images' AND auth.uid()::text = (storage.foldername(name))[1]);
```

### For `team-logos` bucket:

**Policy 1: Allow authenticated users to upload**
```sql
CREATE POLICY "Allow authenticated users to upload team logos"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'team-logos');
```

**Policy 2: Allow public read access**
```sql
CREATE POLICY "Allow public read access to team logos"
ON storage.objects
FOR SELECT
TO public
USING (bucket_id = 'team-logos');
```

**Policy 3: Allow users to update their team logos**
```sql
CREATE POLICY "Allow users to update team logos"
ON storage.objects
FOR UPDATE
TO authenticated
USING (bucket_id = 'team-logos');
```

## Verification

After setup, verify the buckets are working:

1. Check that both buckets appear in the Storage dashboard
2. Verify the buckets are marked as **Public**
3. Test uploading a file through the Supabase dashboard
4. Copy the public URL and verify you can access it in a browser

## Storage Folder Structure

### enhanced-images bucket:
```
enhanced-images/
├── user-{user_id}/
│   ├── enhanced_{image_id}.jpg
│   ├── original_{image_id}.jpg
│   └── ...
```

### team-logos bucket:
```
team-logos/
├── {team_id}.png
├── {team_id}_home.png
├── {team_id}_away.png
└── ...
```

## Notes

- Storage URLs are public and can be accessed without authentication
- Files are organized by user ID for enhanced images
- Database stores both the storage path and public URL
- Backend handles all upload/delete operations via Supabase client
