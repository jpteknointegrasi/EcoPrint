-- Advisor fix: pin search_path on the pure helper functions
alter function public._ms(timestamptz) set search_path = '';
alter function public._t(text, text) set search_path = '';
alter function public._valid_images(jsonb) set search_path = '';
