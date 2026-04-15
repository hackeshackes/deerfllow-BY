import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  CreateCustomSkillRequest,
  RateSkillRequest,
  ShareSkillRequest,
  UpdateUserSkillConfigRequest,
} from "./api";
import {
  createCustomSkill,
  disableUserSkill,
  enableSkill,
  enableUserSkill,
  loadCustomSkills,
  loadSharedSkills,
  loadUserSkills,
  rateSkill,
  shareSkill,
  unshareSkill,
  updateUserSkillConfig,
} from "./api";

import { loadSkills } from ".";

export function useSkills() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["skills"],
    queryFn: () => loadSkills(),
  });
  return { skills: data ?? [], isLoading, error };
}

export function useEnableSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      skillName,
      enabled,
    }: {
      skillName: string;
      enabled: boolean;
    }) => {
      await enableSkill(skillName, enabled);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useUserSkills() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["user-skills"],
    queryFn: () => loadUserSkills(),
  });
  return { skills: data ?? [], isLoading, error };
}

export function useUpdateUserSkillConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      skillName,
      request,
    }: {
      skillName: string;
      request: UpdateUserSkillConfigRequest;
    }) => {
      return updateUserSkillConfig(skillName, request);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-skills"] });
    },
  });
}

export function useEnableUserSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (skillName: string) => {
      return enableUserSkill(skillName);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-skills"] });
    },
  });
}

export function useDisableUserSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (skillName: string) => {
      return disableUserSkill(skillName);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-skills"] });
    },
  });
}

export function useShareSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      skillName,
      request,
    }: {
      skillName: string;
      request: ShareSkillRequest;
    }) => {
      return shareSkill(skillName, request);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shared-skills"] });
    },
  });
}

export function useUnshareSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (skillName: string) => {
      return unshareSkill(skillName);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shared-skills"] });
    },
  });
}

export function useRateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      skillName,
      request,
    }: {
      skillName: string;
      request: RateSkillRequest;
    }) => {
      return rateSkill(skillName, request);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["user-skills"] });
    },
  });
}

export function useSharedSkills() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["shared-skills"],
    queryFn: () => loadSharedSkills(),
  });
  return { skills: data ?? [], isLoading, error };
}

export function useCustomSkills() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["custom-skills"],
    queryFn: () => loadCustomSkills(),
  });
  return { skills: data ?? [], isLoading, error };
}

export function useCreateCustomSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (request: CreateCustomSkillRequest) => {
      return createCustomSkill(request);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["custom-skills"] });
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
      void queryClient.invalidateQueries({ queryKey: ["user-skills"] });
    },
  });
}
