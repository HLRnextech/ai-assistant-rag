import React, { useState } from 'react';
import { Star } from 'lucide-react';

export const StarRating = ({ rating, onRatingChange, disabled = false }) => {
  const [hoverRating, setHoverRating] = useState(0);

  const handleMouseEnter = (index) => {
    if (disabled) return;
    setHoverRating(index);
  };

  const handleMouseLeave = () => {
    if (disabled) return;
    setHoverRating(0);
  };

  const handleClick = (index) => {
    if (disabled) return;
    onRatingChange(index);
  };

  return (
    <div className="flex space-x-1">
      {[1, 2, 3, 4, 5].map((index) => (
        <Star
          fill={(hoverRating || rating) >= index ? 'rgb(250 204 21)' : 'none'}
          stroke='rgb(250 204 21)'
          key={index}
          className={`w-8 h-8 ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'} ${(hoverRating || rating) >= index ? 'text-yellow-400' : 'text-gray-300'}`}
          onMouseEnter={() => handleMouseEnter(index)}
          onMouseLeave={handleMouseLeave}
          onClick={() => handleClick(index)}
        />
      ))}
    </div>
  );
};