import { NextRequest, NextResponse } from 'next/server';
import { ulid } from 'ulid';
import { prisma } from '@/lib/prisma';
import { uploadToS3 } from '@/lib/s3';

// Chat attachments (task T9). Multipart upload → minio/S3 → Asset row. The
// composer uploads here first, then references the returned URLs in the chat
// message body, so the worker's agent (and the transcript) see plain URLs — no
// attachment plumbing in the turn pipeline.

const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB per file
const MAX_FILES = 5;

function safeName(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]+/g, '_').slice(-80) || 'file';
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await prisma.project.findUnique({ where: { id }, select: { id: true } });
  if (!project) {
    return NextResponse.json({ error: 'project not found' }, { status: 404 });
  }

  const form = await req.formData().catch(() => null);
  if (!form) {
    return NextResponse.json({ error: 'multipart form data required' }, { status: 400 });
  }
  const files = form.getAll('files').filter((f): f is File => f instanceof File);
  if (files.length === 0) {
    return NextResponse.json({ error: 'no files provided' }, { status: 400 });
  }
  if (files.length > MAX_FILES) {
    return NextResponse.json({ error: `max ${MAX_FILES} files per upload` }, { status: 400 });
  }
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) {
      return NextResponse.json(
        { error: `${file.name} exceeds the 10 MB limit` },
        { status: 413 }
      );
    }
  }

  const uploaded = [];
  for (const file of files) {
    const assetId = ulid();
    const filename = `${assetId}-${safeName(file.name)}`;
    const key = `attachments/${id}/${filename}`;
    const mimeType = file.type || 'application/octet-stream';
    const url = await uploadToS3(key, Buffer.from(await file.arrayBuffer()), mimeType);
    const asset = await prisma.asset.create({
      data: {
        id: assetId,
        projectId: id,
        filename,
        originalFilename: file.name,
        url,
        size: file.size,
        mimeType,
      },
    });
    uploaded.push({
      id: asset.id,
      url: asset.url,
      filename: file.name,
      mimeType,
      size: file.size,
    });
  }

  return NextResponse.json({ attachments: uploaded }, { status: 201 });
}
