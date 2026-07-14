-- CreateEnum
CREATE TYPE "ProjectStatus" AS ENUM ('ACTIVE', 'HIDE', 'NOT_ACTIVE');

-- CreateEnum
CREATE TYPE "GenerationStatus" AS ENUM ('DRAFT', 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED');

-- CreateEnum
CREATE TYPE "ChatRole" AS ENUM ('USER', 'ASSISTANT');

-- CreateEnum
CREATE TYPE "ChatMessageStatus" AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "RequirementType" AS ENUM ('EXPLICIT', 'HIDDEN');

-- CreateEnum
CREATE TYPE "Severity" AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');

-- CreateEnum
CREATE TYPE "HarnessResultValue" AS ENUM ('SUCCESS', 'FAIL');

-- CreateEnum
CREATE TYPE "HarnessRunStatus" AS ENUM ('OK', 'INCONCLUSIVE');

-- CreateTable
CREATE TABLE "Project" (
    "id" TEXT NOT NULL,
    "title" TEXT,
    "desc" TEXT,
    "logo" TEXT,
    "prompt" TEXT,
    "status" "ProjectStatus" NOT NULL DEFAULT 'NOT_ACTIVE',
    "generationStatus" "GenerationStatus" NOT NULL DEFAULT 'DRAFT',
    "harnessRunning" BOOLEAN NOT NULL DEFAULT false,
    "harnessRunRequested" BOOLEAN NOT NULL DEFAULT false,
    "agentSessionId" TEXT,
    "assignedWorker" TEXT,
    "affinityExpiresAt" TIMESTAMP(3),
    "previewPort" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Project_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Asset" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "originalFilename" TEXT,
    "url" TEXT NOT NULL,
    "size" INTEGER NOT NULL,
    "mimeType" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Asset_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ChatMessage" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "role" "ChatRole" NOT NULL,
    "content" TEXT NOT NULL,
    "thinking" TEXT,
    "stage" TEXT,
    "activity" TEXT,
    "activityLog" JSONB,
    "status" "ChatMessageStatus" NOT NULL DEFAULT 'COMPLETED',
    "assignedWorker" TEXT,
    "leaseExpiresAt" TIMESTAMP(3),
    "attempts" INTEGER NOT NULL DEFAULT 0,
    "error" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ChatMessage_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AgentSessionEntry" (
    "id" TEXT NOT NULL,
    "projectKey" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "subpath" TEXT,
    "seq" BIGINT NOT NULL,
    "entry" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AgentSessionEntry_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Worker" (
    "id" TEXT NOT NULL,
    "lastSeen" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Worker_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "HarnessRequirement" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "excerpt" TEXT,
    "description" TEXT NOT NULL,
    "type" "RequirementType" NOT NULL DEFAULT 'EXPLICIT',
    "severity" "Severity" NOT NULL DEFAULT 'MEDIUM',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "HarnessRequirement_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "HarnessResult" (
    "requirementId" TEXT NOT NULL,
    "result" "HarnessResultValue",
    "evidence" TEXT,
    "runStatus" "HarnessRunStatus" NOT NULL DEFAULT 'INCONCLUSIVE',
    "lastVerifiedSha" TEXT,
    "watchedPaths" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "runAt" TIMESTAMP(3),
    "isStale" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "HarnessResult_pkey" PRIMARY KEY ("requirementId")
);

-- CreateIndex
CREATE INDEX "Project_updatedAt_idx" ON "Project"("updatedAt" DESC);

-- CreateIndex
CREATE INDEX "Asset_projectId_createdAt_idx" ON "Asset"("projectId", "createdAt");

-- CreateIndex
CREATE INDEX "ChatMessage_projectId_createdAt_idx" ON "ChatMessage"("projectId", "createdAt");

-- CreateIndex
CREATE INDEX "ChatMessage_assignedWorker_status_idx" ON "ChatMessage"("assignedWorker", "status");

-- CreateIndex
CREATE INDEX "ChatMessage_status_idx" ON "ChatMessage"("status");

-- CreateIndex
CREATE INDEX "ChatMessage_status_leaseExpiresAt_idx" ON "ChatMessage"("status", "leaseExpiresAt");

-- CreateIndex
CREATE INDEX "AgentSessionEntry_projectKey_sessionId_subpath_seq_idx" ON "AgentSessionEntry"("projectKey", "sessionId", "subpath", "seq");

-- CreateIndex
CREATE INDEX "HarnessRequirement_projectId_idx" ON "HarnessRequirement"("projectId");

-- AddForeignKey
ALTER TABLE "Asset" ADD CONSTRAINT "Asset_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ChatMessage" ADD CONSTRAINT "ChatMessage_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "HarnessRequirement" ADD CONSTRAINT "HarnessRequirement_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "HarnessResult" ADD CONSTRAINT "HarnessResult_requirementId_fkey" FOREIGN KEY ("requirementId") REFERENCES "HarnessRequirement"("id") ON DELETE CASCADE ON UPDATE CASCADE;
