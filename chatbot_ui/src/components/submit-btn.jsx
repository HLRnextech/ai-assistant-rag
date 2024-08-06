import React from "react";
import { Button } from "@/components/ui/button.jsx";
import SubmitIcon from "@/assets/submit.svg";
import { DEFAULT_SECONDARY_COLOR } from "@/config";

export const SubmitBtn = ({ onClick, disabled, bgcolor }) => (
  <Button
    type="submit"
    disabled={disabled}
    className="bg-[var(--bgcolor)] rounded-full hover:bg-submitIcon w-8 h-8 p-1 aspect-square mt-1"
    style={{
      '--bgcolor': bgcolor || DEFAULT_SECONDARY_COLOR
    }}
    onClick={onClick}
  >
    <SubmitIcon />
  </Button>
);

