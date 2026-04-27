"use client";

import { BlocksIcon, PlusIcon, Share2Icon, StarIcon, Trash2Icon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateCustomSkill,
  useDeleteCustomSkill,
  useDisableUserSkill,
  useEnableUserSkill,
  useMyCustomSkills,
  useRateSkill,
  useShareSkill,
  useUnshareSkill,
  useUserSkills,
} from "@/core/skills/hooks";
import type { UserSkillConfig } from "@/core/skills/type";

const DEFAULT_SKILL_TEMPLATE = `---
name: my-custom-skill
description: Enter your skill description here
author: Your Name
version: 1.0.0
---

# My Custom Skill

Describe what this skill does here.

## Usage

Explain how to use this skill.

## Examples

Provide some examples.
`;

export function UserSkillsPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <div className="rounded-3xl border bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 px-6 py-6 text-white shadow-sm">
        <div className="mt-3 text-2xl font-semibold tracking-tight">用户技能管理</div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-200">
          配置个人技能偏好、创建自定义技能、共享技能给其他用户、对技能进行评分
        </p>
      </div>

      <Tabs defaultValue="all">
        <div className="flex justify-between">
          <TabsList>
            <TabsTrigger value="all">全部技能</TabsTrigger>
            <TabsTrigger value="custom">我的创建</TabsTrigger>
            <TabsTrigger value="shared">共享记录</TabsTrigger>
          </TabsList>
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <PlusIcon className="size-4" />
            创建技能
          </Button>
        </div>

        <TabsContent value="all">
          <AllSkillsList />
        </TabsContent>
        <TabsContent value="custom">
          <CustomSkillsList />
        </TabsContent>
        <TabsContent value="shared">
          <SharedSkillsList />
        </TabsContent>
      </Tabs>

      <CreateSkillDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
      />
    </div>
  );
}

function AllSkillsList() {
  const { skills, isLoading, error } = useUserSkills();
  const { mutate: enableUserSkill } = useEnableUserSkill();
  const { mutate: disableUserSkill } = useDisableUserSkill();

  if (isLoading) return <div className="text-muted-foreground text-sm">加载中...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {skills.map((skill) => (
        <Card key={skill.skill_name}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <BlocksIcon className="size-5" />
              {skill.display_name}
            </CardTitle>
            <CardDescription className="line-clamp-2">
              {skill.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Switch
                  checked={skill.enabled}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      enableUserSkill(skill.skill_name);
                    } else {
                      disableUserSkill(skill.skill_name);
                    }
                  }}
                />
                <span className="text-sm">{skill.enabled ? "已启用" : "已禁用"}</span>
              </div>
              {skill.average_rating !== null && (
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <StarIcon className="size-4 fill-yellow-400 text-yellow-400" />
                  <span>{skill.average_rating.toFixed(1)}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function CustomSkillsList() {
  const { skills, isLoading, error, refetch } = useMyCustomSkills();
  const deleteCustomSkill = useDeleteCustomSkill();
  const [deleteConfirm, setDeleteConfirm] = useState<{ open: boolean; skillName: string | null }>({
    open: false,
    skillName: null,
  });

  const handleDelete = async () => {
    if (!deleteConfirm.skillName) return;
    try {
      await deleteCustomSkill.mutateAsync(deleteConfirm.skillName);
      await refetch();
      setDeleteConfirm({ open: false, skillName: null });
    } catch (err) {
      alert(err instanceof Error ? err.message : "删除失败");
    }
  };

  if (isLoading) return <div className="text-muted-foreground text-sm">加载中...</div>;
  if (error) return <div>Error: {error.message}</div>;

  if (skills.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <BlocksIcon className="size-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">暂无自定义技能</p>
        <p className="text-sm text-muted-foreground">点击右上角&quot;创建技能&quot;开始</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {skills.map((skill) => (
          <Card key={skill.name}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <BlocksIcon className="size-5" />
                {skill.name}
              </CardTitle>
              <CardDescription className="line-clamp-2">
                {skill.description}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <span className={skill.enabled ? "text-green-600" : "text-muted-foreground"}>
                    {skill.enabled ? "已启用" : "已禁用"}
                  </span>
                  {skill.version && (
                    <span className="text-muted-foreground">v{skill.version}</span>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setDeleteConfirm({ open: true, skillName: skill.name })}
                >
                  <Trash2Icon className="size-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={deleteConfirm.open} onOpenChange={(open) => !open && setDeleteConfirm({ open: false, skillName: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除技能</DialogTitle>
            <DialogDescription>
              确定要删除技能 &quot;{deleteConfirm.skillName}&quot; 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm({ open: false, skillName: null })}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleteCustomSkill.isPending}>
              {deleteCustomSkill.isPending ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function SharedSkillsList() {
  const [shareDialog, setShareDialog] = useState<{ open: boolean; skill: UserSkillConfig | null }>({
    open: false,
    skill: null,
  });
  const [rateDialog, setRateDialog] = useState<{ open: boolean; skill: UserSkillConfig | null }>({
    open: false,
    skill: null,
  });

  const { skills, isLoading, error } = useUserSkills();
  const { mutate: shareSkill } = useShareSkill();
  const { mutate: unshareSkill } = useUnshareSkill();
  const { mutate: rateSkill } = useRateSkill();

  if (isLoading) return <div className="text-muted-foreground text-sm">加载中...</div>;
  if (error) return <div>Error: {error.message}</div>;

  const handleShare = (skill: UserSkillConfig, visibility: "public" | "workspace") => {
    shareSkill({
      skillName: skill.skill_name,
      request: { visibility },
    });
    setShareDialog({ open: false, skill: null });
  };

  const handleUnshare = (skillName: string) => {
    unshareSkill(skillName);
  };

  const handleRate = (skill: UserSkillConfig, rating: number, comment: string) => {
    rateSkill({
      skillName: skill.skill_name,
      request: { rating, comment: comment || undefined },
    });
    setRateDialog({ open: false, skill: null });
  };

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {skills.map((skill) => (
          <Card key={skill.skill_name}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <BlocksIcon className="size-5" />
                {skill.display_name}
              </CardTitle>
              <CardDescription className="line-clamp-2">
                {skill.description}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                {skill.average_rating !== null && (
                  <div className="flex items-center gap-1 text-sm">
                    <StarIcon className="size-4 fill-yellow-400 text-yellow-400" />
                    <span>{skill.average_rating.toFixed(1)}</span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" className="flex-1" onClick={() => setShareDialog({ open: true, skill })}>
                  <Share2Icon className="size-4" />
                  分享
                </Button>
                <Button size="sm" variant="outline" className="flex-1" onClick={() => setRateDialog({ open: true, skill })}>
                  <StarIcon className="size-4" />
                  评分
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <ShareSkillDialog
        open={shareDialog.open}
        skill={shareDialog.skill}
        onClose={() => setShareDialog({ open: false, skill: null })}
        onShare={handleShare}
        onUnshare={handleUnshare}
      />

      <RateSkillDialog
        open={rateDialog.open}
        skill={rateDialog.skill}
        onClose={() => setRateDialog({ open: false, skill: null })}
        onRate={handleRate}
      />
    </>
  );
}

function ShareSkillDialog({
  open,
  skill,
  onClose,
  onShare,
  onUnshare,
}: {
  open: boolean;
  skill: UserSkillConfig | null;
  onClose: () => void;
  onShare: (skill: UserSkillConfig, visibility: "public" | "workspace") => void;
  onUnshare: (skillName: string) => void;
}) {
  const [visibility, setVisibility] = useState<"public" | "workspace">("public");

  if (!skill) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>分享技能: {skill.display_name}</DialogTitle>
          <DialogDescription>选择技能的可见性范围</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-4">
            <div>
              <div className="font-medium">公开</div>
              <div className="text-sm text-muted-foreground">所有用户可见</div>
            </div>
            <Switch
              checked={visibility === "public"}
              onCheckedChange={(checked) => setVisibility(checked ? "public" : "workspace")}
            />
          </div>
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button variant="destructive" onClick={() => onUnshare(skill.skill_name)}>
            取消分享
          </Button>
          <Button onClick={() => onShare(skill, visibility)}>确认分享</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RateSkillDialog({
  open,
  skill,
  onClose,
  onRate,
}: {
  open: boolean;
  skill: UserSkillConfig | null;
  onClose: () => void;
  onRate: (skill: UserSkillConfig, rating: number, comment: string) => void;
}) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");

  if (!skill) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>评分技能: {skill.display_name}</DialogTitle>
          <DialogDescription>对技能进行评分并提供反馈</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRating(star)}
                className="p-1 transition-transform hover:scale-110"
              >
                <StarIcon
                  className={`size-8 ${star <= rating ? "fill-yellow-400 text-yellow-400" : "text-muted"}`}
                />
              </button>
            ))}
          </div>
          <Textarea
            placeholder="添加评论（可选）..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button onClick={() => onRate(skill, rating, comment)}>提交评分</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreateSkillDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [content, setContent] = useState(DEFAULT_SKILL_TEMPLATE);
  const [error, setError] = useState<string | null>(null);
  const { mutate: createSkill, isPending } = useCreateCustomSkill();

  const handleCreate = () => {
    if (!name.trim()) {
      setError("技能名称不能为空");
      return;
    }
    setError(null);
    createSkill(
      { name: name.trim(), content },
      {
        onSuccess: () => {
          setName("");
          setContent(DEFAULT_SKILL_TEMPLATE);
          onClose();
        },
        onError: (err: Error) => {
          setError(err.message);
        },
      },
    );
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setName("");
      setContent(DEFAULT_SKILL_TEMPLATE);
      setError(null);
    }
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>创建自定义技能</DialogTitle>
          <DialogDescription>
            创建一个新的自定义技能。技能将以 Markdown 格式保存。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">技能名称</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-custom-skill"
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">SKILL.md 内容</label>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Enter skill content..."
              className="mt-1 font-mono text-sm"
              rows={20}
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            取消
          </Button>
          <Button onClick={handleCreate} disabled={isPending}>
            {isPending ? "创建中..." : "创建技能"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
