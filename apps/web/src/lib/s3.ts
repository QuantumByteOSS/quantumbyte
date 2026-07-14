import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

// S3 / minio config — env names and defaults mirror the worker's S3Config
// (apps/worker/mcp_servers/context.py) so one .env drives both apps.
const ENDPOINT = process.env.S3_ENDPOINT ?? 'http://localhost:9000';
const PUBLIC_URL = process.env.S3_PUBLIC_URL ?? 'http://localhost:9000';
const ACCESS_KEY = process.env.S3_ACCESS_KEY ?? 'quantumbyte';
const SECRET_KEY = process.env.S3_SECRET_KEY ?? 'quantumbyte';
export const S3_BUCKET = process.env.S3_BUCKET ?? 'qb-assets';

// forcePathStyle: minio serves buckets as path prefixes, not subdomains.
export const s3 = new S3Client({
  endpoint: ENDPOINT,
  region: process.env.S3_REGION ?? 'us-east-1',
  credentials: { accessKeyId: ACCESS_KEY, secretAccessKey: SECRET_KEY },
  forcePathStyle: true,
});

/** Upload a buffer and return its public direct URL (same shape the worker's
 * qb-designer tools produce for Asset.url). */
export async function uploadToS3(
  key: string,
  body: Buffer,
  contentType: string
): Promise<string> {
  await s3.send(
    new PutObjectCommand({
      Bucket: S3_BUCKET,
      Key: key,
      Body: body,
      ContentType: contentType,
    })
  );
  return `${PUBLIC_URL}/${S3_BUCKET}/${key}`;
}
