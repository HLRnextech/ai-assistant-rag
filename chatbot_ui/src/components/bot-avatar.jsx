import React from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar.jsx";

const BotAvatar = ({ url, name }) => (
  <Avatar>
    <AvatarImage src={url} alt={name} />
    <AvatarFallback>{name}</AvatarFallback>
  </Avatar>
);

export default BotAvatar;
