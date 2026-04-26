"use client";

import {
  BellIcon,
  InfoIcon,
  BrainIcon,
  PaletteIcon,
  BlocksIcon,
  DatabaseIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AboutSettingsPage } from "@/components/workspace/settings/about-settings-page";
import { AppearanceSettingsPage } from "@/components/workspace/settings/appearance-settings-page";
import { MemorySettingsPage } from "@/components/workspace/settings/memory-settings-page";
import { NotificationSettingsPage } from "@/components/workspace/settings/notification-settings-page";
import { UserKnowledgePage } from "@/components/workspace/settings/user-knowledge-page";
import { UserSkillsPage } from "@/components/workspace/settings/user-skills-page";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

type SettingsSection =
  | "appearance"
  | "memory"
  | "notification"
  | "skills"
  | "knowledge"
  | "about";

type SettingsDialogProps = React.ComponentProps<typeof Dialog> & {
  defaultSection?: SettingsSection;
};

export function SettingsDialog(props: SettingsDialogProps) {
  const { defaultSection = "appearance", ...dialogProps } = props;
  const { t } = useI18n();
  const [activeSection, setActiveSection] =
    useState<SettingsSection>(defaultSection);

  useEffect(() => {
    // When opening the dialog, ensure the active section follows the caller's intent.
    // This allows triggers like "About" to open the dialog directly on that page.
    if (dialogProps.open) {
      setActiveSection(defaultSection);
    }
  }, [defaultSection, dialogProps.open]);

  const sections = useMemo(
    () => [
      {
        id: "appearance",
        label: t.settings.sections.appearance,
        icon: PaletteIcon,
      },
      {
        id: "notification",
        label: t.settings.sections.notification,
        icon: BellIcon,
      },
      {
        id: "memory",
        label: t.settings.sections.memory,
        icon: BrainIcon,
      },
      {
        id: "skills",
        label: t.settings.sections.skills,
        icon: BlocksIcon,
      },
      {
        id: "knowledge",
        label: t.settings.sections.knowledge,
        icon: DatabaseIcon,
      },
      { id: "about", label: t.settings.sections.about, icon: InfoIcon },
    ],
    [
      t.settings.sections.appearance,
      t.settings.sections.memory,
      t.settings.sections.notification,
      t.settings.sections.skills,
      t.settings.sections.knowledge,
      t.settings.sections.about,
    ],
  );
  return (
    <Dialog
      {...dialogProps}
      onOpenChange={(open) => props.onOpenChange?.(open)}
    >
      <DialogContent
        className="flex h-[75vh] max-h-[calc(100vh-2rem)] flex-col sm:max-w-5xl md:max-w-6xl"
        aria-describedby={undefined}
      >
        <DialogHeader className="gap-1">
          <DialogTitle>{t.settings.title}</DialogTitle>
          <p className="text-muted-foreground text-sm">
            {t.settings.description}
          </p>
        </DialogHeader>
        <div className="grid min-h-0 flex-1 gap-4 md:grid-cols-[220px_1fr]">
          <nav className="bg-sidebar min-h-0 overflow-y-auto rounded-lg border p-2">
            <ul className="space-y-1 pr-1">
              {sections.map(({ id, label, icon: Icon }) => {
                const active = activeSection === id;
                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => setActiveSection(id as SettingsSection)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )}
                    >
                      <Icon className="size-4" />
                      <span>{label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          <ScrollArea className="h-full min-h-0 rounded-lg border">
            <div className="space-y-8 p-6">
              {activeSection === "appearance" && <AppearanceSettingsPage />}
              {activeSection === "memory" && <MemorySettingsPage />}
              {activeSection === "notification" && <NotificationSettingsPage />}
              {activeSection === "skills" && <UserSkillsPage />}
              {activeSection === "knowledge" && <UserKnowledgePage />}
              {activeSection === "about" && <AboutSettingsPage />}
            </div>
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
