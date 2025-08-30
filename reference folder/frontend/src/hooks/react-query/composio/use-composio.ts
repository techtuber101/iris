'use client';

import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { 
  composioApi, 
  type ComposioToolkitsResponse,
  type CompositoCategoriesResponse,
  type CreateComposioProfileRequest,
  type CreateComposioProfileResponse,
} from './utils';
import { composioKeys } from './keys';
import { toast } from 'sonner';

export const useComposioCategories = () => {
  return useQuery({
    queryKey: composioKeys.categories(),
    queryFn: async (): Promise<CompositoCategoriesResponse> => {
      const result = await composioApi.getCategories();
      console.log('📂 Composio Categories:', result);
      return result;
    },
    staleTime: 10 * 60 * 1000,
    retry: 2,
  });
};

export const useComposioToolkits = (search?: string, category?: string) => {
  return useQuery({
    queryKey: composioKeys.toolkits(search, category),
    queryFn: async (): Promise<ComposioToolkitsResponse> => {
      const result = await composioApi.getToolkits(search, category);
      console.log('🔍 Composio Toolkits:', result);
      return result;
    },
    staleTime: 5 * 60 * 1000, 
    retry: 2,
  });
};

export const useComposioToolkitIcon = (toolkitSlug: string, options?: { enabled?: boolean }) => {
  return useQuery({
    queryKey: ['composio', 'toolkit-icon', toolkitSlug],
    queryFn: async (): Promise<{ success: boolean; icon_url?: string }> => {
      const result = await composioApi.getToolkitIcon(toolkitSlug);
      console.log(`🎨 Composio Icon for ${toolkitSlug}:`, result);
      return result;
    },
    enabled: options?.enabled !== undefined ? options.enabled : !!toolkitSlug,
    staleTime: 60 * 60 * 1000,
    retry: 2,
  });
};

export const useCreateComposioProfile = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (request: CreateComposioProfileRequest): Promise<CreateComposioProfileResponse> => {
      return await composioApi.createProfile(request);
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: composioKeys.profiles.all() });
      toast.success(`Connected to ${variables.profile_name}!`);
      
      // If there's a redirect URL, open it automatically
      if (data.redirect_url) {
        console.log('🔗 Opening OAuth URL:', data.redirect_url);
        window.open(data.redirect_url, '_blank', 'width=600,height=700,resizable=yes,scrollbars=yes');
      }
    },
    onError: (error) => {
      console.error('Failed to create Composio profile:', error);
      toast.error(error.message || 'Failed to create profile');
    },
  });
};

export const useInvalidateComposioQueries = () => {
  const queryClient = useQueryClient();
  
  return () => {
    queryClient.invalidateQueries({ queryKey: composioKeys.all });
  };
}; 