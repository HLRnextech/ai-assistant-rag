import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card.jsx';
import { Button } from "@/components/ui/button.jsx";
import CloseIcon from "@/assets/close.svg";

const Tooltip = ({ content, onClose, onTooltipClick }) => {
  const [showTooltip, setShowTooltip] = useState(true);

  const toggleTooltip = () => {
    if (showTooltip && onClose) {
      onClose();
    }
    setShowTooltip(!showTooltip);
  };

  const handleCardContentClick = () => {
    if (onTooltipClick) {
      onTooltipClick();
    }
  }

  return (
    <div className="fixed bottom-0 right-0 mb-12 mr-12 max-w-md">
      {showTooltip && (
        <Card className="rounded-br-none">
          <CardContent
            className={`p-3 ${onTooltipClick ? 'cursor-pointer' : ''}`}
            onClick={handleCardContentClick}
          >
            {content}
          </CardContent>
          <Button
            onClick={toggleTooltip}
            className="bg-closeBtn rounded-full hover:bg-closeBtn w-8 h-8 p-1 aspect-square mt-1 absolute -right-4 -top-4 !shadow-md"
          >
            <CloseIcon className="w-4 h-4 text-white" />
          </Button>
        </Card>
      )}
    </div>
  );
};

export default Tooltip;